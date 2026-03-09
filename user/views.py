from django.db.models import Q
from rest_framework.decorators import permission_classes, api_view
from rest_framework.views import APIView
from common.permissions import IsValidated, AllowAny
from environment.variables import EnvironmentVariable
from .serializers import UserLookupSerializer, FoodItemSerializer,UserShortSerializer, UserUpdateSerializer, LootBoxListSerializer
from common.utils import CommonUtils, WalletUtils
from .models import *
from exceptions import InvalidParameterException
from rest_framework.response import Response
from rest_framework import status
import logging
from .services import LootBoxService
from .tasks import nft_sync
from .utils import generate_unique_referral_code, validate_referral

logger = logging.getLogger(__name__)


class LoginView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        wallet_address = request.data.get("wallet_address", None)
        challenge = request.data.get("challenge", None)
        signature = request.data.get("signature", None)

        if wallet_address == None or wallet_address == "":
            raise InvalidParameterException("wallet_address")

        if challenge == None or challenge == "":
            raise InvalidParameterException("challenge")
        if signature == None or signature == "":
            raise InvalidParameterException("signature")

        if WalletUtils.validateSignature(wallet_address, challenge, signature) is True:
            user = User.objects.filter(Q(username=wallet_address) | Q(wallet_address=wallet_address)).first()
            if user is None:
                code = generate_unique_referral_code()
                user = User.objects.create(username=wallet_address, wallet_address=wallet_address, referral_code=code)
            response = CommonUtils.create_access(user)
            return CommonUtils.dispatch_success(response)
        else:
            raise InvalidParameterException("Invalid Signature. Please login with valid signature.")


class CurrentUserView(APIView):
    permission_classes = (AllowAny, IsValidated,)
    serializer = UserLookupSerializer

    def get(self, request):
        return CommonUtils.dispatch_success(self.serializer(request.user).data)


class SignatureView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request):
        """
        This method pulls the message to be signed by the user wallet
        @param request: Http Request
        @return: message to be signed by wallet
        """
        wallet_address = request.GET.get("wallet_address", None)

        if wallet_address == None or wallet_address == "":
            raise InvalidParameterException("wallet_address")

        # wallet_address = Web3.to_checksum_address(wallet_address)

        return CommonUtils.dispatch_success(WalletUtils.generateMessageHash(wallet_address))


class UpdateProfileView(APIView):
    permission_classes = (IsValidated,)

    def patch(self, request):
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return CommonUtils.dispatch_success(UserLookupSerializer(request.user).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




class VerifyReferralCodeView(APIView):
    permission_classes = (IsValidated,)

    def post(self, request):
        """
        Verify if a referral code is valid
        Returns referrer information if valid
        """
        referral_code = request.data.get('referral_code')

        if not referral_code:
            return Response({
                "status": "error",
                "message": "Referral code is required"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Clean up the referral code (remove whitespace, convert to uppercase)
        referral_code = referral_code.strip().upper()

        # Look for user with this referral code
        try:
            referrer = User.objects.get(referral_code=referral_code, is_active=True)

            if referral_code:
                referred_by_user, error_message = validate_referral(request.user, referral_code)
                if referred_by_user:
                    request.user.referred_by = referred_by_user
                    request.user.save()

            return CommonUtils.dispatch_success(UserLookupSerializer(request.user).data)

        except User.DoesNotExist:
            return Response({
                "status": "error",
                "valid": False,
                "message": "Invalid referral code"
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                "status": "error",
                "message": "Failed to verify referral code"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Food Inventory System Views
class FoodItemListView(APIView):
    """Get all available food items"""
    permission_classes = (IsValidated,)

    def get(self, request):
        """Get all active food items"""
        food_items = FoodItem.objects.filter(active=True).order_by('name')

        serializer = FoodItemSerializer(food_items, many=True)
        return CommonUtils.dispatch_success({
            "food_items": serializer.data,
            "total_items": len(serializer.data),
        })


class FoodInventoryView(APIView):
    """Manage user's food inventory"""
    permission_classes = (IsValidated,)

    def get(self, request):
        """Get user's current food inventory"""
        user = request.user
        inventory_summary = user.get_food_inventory_summary()

        # Add consumed food points to the response
        consumed_points = user.get_consumed_food_points()

        return CommonUtils.dispatch_success({
            'inventory': inventory_summary,
            'consumed_food_points': consumed_points,
            'total_points': user.total_points
        })

    def post(self, request):
        """Add food items to user's inventory (admin only)"""
        user = request.user

        # Check if user is admin (you can modify this logic as needed)
        if not user.is_staff:
            return Response({
                "status": "error",
                "message": "Only administrators can add food to inventory."
            }, status=status.HTTP_403_FORBIDDEN)

        food_item_id = request.data.get("food_item_id")
        quantity = request.data.get("quantity")

        if not food_item_id or not quantity:
            return Response({
                "status": "error",
                "message": "food_item_id and quantity are required."
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            food_item = FoodItem.objects.get(id=food_item_id, active=True)
        except FoodItem.DoesNotExist:
            return Response({
                "status": "error",
                "message": "Food item not found or inactive."
            }, status=status.HTTP_404_NOT_FOUND)

        try:
            quantity = int(quantity)
            if quantity <= 0:
                raise ValueError()
        except (ValueError, TypeError):
            return Response({
                "status": "error",
                "message": "Quantity must be a positive integer."
            }, status=status.HTTP_400_BAD_REQUEST)

        # Add food to inventory
        inventory = user.add_food_to_inventory(food_item, quantity)

        return CommonUtils.dispatch_success({
            'message': f'Added {quantity} {food_item.display_name} to inventory',
            'inventory_item': {
                'food_item': {
                    'id': food_item.id,
                    'name': food_item.name,
                    'display_name': food_item.display_name,
                    'emoji': food_item.emoji,
                    'points_per_item': food_item.points_per_item,
                },
                'quantity': inventory.quantity,
                'potential_points': inventory.quantity * food_item.points_per_item
            }
        }, status_code=status.HTTP_201_CREATED)



class UserRankView(APIView):
    """Get user's total points and leaderboard rank"""
    permission_classes = (IsValidated,)

    def get(self, request):
        user = request.user

        higher_ranked = User.objects.filter(
            is_superuser=False
        ).filter(
            Q(total_points__gt=user.total_points) |
            Q(total_points=user.total_points, date_joined__lt=user.date_joined)
        ).count()

        total_users = User.objects.filter(is_superuser=False).count()
        user_rank = higher_ranked + 1

        return CommonUtils.dispatch_success({
            "user": UserShortSerializer(user).data,
            "total_points": user.total_points,
            "rank": user_rank,
            "total_users": total_users,
            "description": f"You are ranked #{user_rank} out of {total_users} users"
        })


# ==================== LOOTBOX SYSTEM VIEWS ====================

class LootBoxListView(APIView):
    """List all available loot boxes"""
    permission_classes = (IsValidated,)

    def get(self, request):
        """Get all active loot boxes with their rewards"""
        try:
            loot_boxes = LootBox.objects.filter(is_active=True)

            return CommonUtils.dispatch_success(LootBoxListSerializer(loot_boxes, many=True).data)
        except Exception as e:
            logger.error(f"Error fetching loot boxes: {e}")
            return Response({
                "status": "error",
                "message": "Failed to fetch loot boxes"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LootBoxPurchaseView(APIView):
    """Purchase loot boxes with food items"""
    permission_classes = (IsValidated,)

    def post(self, request, loot_box_id):
        """Purchase one or more loot boxes"""
        user = request.user
        quantity = request.data.get('quantity', 1)

        # Validate quantity
        try:
            quantity = int(quantity)
            if quantity < 1:
                raise ValueError()
        except (ValueError, TypeError):
            return Response({
                "status": "error",
                "message": "Quantity must be a positive integer"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Purchase loot box
            purchase = LootBoxService.purchase_loot_box(user, loot_box_id, quantity)

            return CommonUtils.dispatch_success({
                'message': f'Successfully purchased {quantity}x {purchase.loot_box.name}!'
            }, status_code=status.HTTP_201_CREATED)

        except ValueError as e:
            return Response({
                "status": "error",
                "message": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error purchasing loot box: {e}")
            return Response({
                "status": "error",
                "message": "Failed to purchase loot box"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LootBoxOpenView(APIView):
    """Open a purchased loot box"""
    permission_classes = (IsValidated,)

    def post(self, request, loot_box_id):
        """Open a loot box and receive a random reward"""
        user = request.user

        try:
            # Open loot box
            reward = LootBoxService.open_loot_box(user, loot_box_id)

            return CommonUtils.dispatch_success({
                "user": UserLookupSerializer(request.user).data,
                'message': f'🎉 You won {reward.quantity_won}x {reward.reward_food_item.display_name}!',
                'reward': {
                    'id': reward.id,
                    'loot_box': {
                        'id': reward.loot_box.id,
                        'name': reward.loot_box.name,
                        'image_url': reward.loot_box.image.url if reward.loot_box.image else '',
                    },
                    'food_item': {
                        'id': reward.reward_food_item.id,
                        'name': reward.reward_food_item.name,
                        'display_name': reward.reward_food_item.display_name,
                        'emoji': reward.reward_food_item.emoji,
                        'points_per_item': reward.reward_food_item.points_per_item,
                    },
                    "image": reward.loot_box_reward.image.url if reward.loot_box_reward.image else '',
                    "title": reward.loot_box_reward.title,
                    "metadata": reward.metadata,
                    "token_id": reward.token_id,
                    "contract_address": reward.contract_address,
                    "status": reward.status,
                    'quantity_won': reward.quantity_won,
                    'rarity': reward.rarity,
                    'total_points_value': reward.quantity_won * reward.reward_food_item.points_per_item,
                    'opened_at': reward.opened_at.isoformat(),
                }
            }, status_code=status.HTTP_201_CREATED)

        except ValueError as e:
            return Response({
                "status": "error",
                "message": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error opening loot box: {e}")
            return Response({
                "status": "error",
                "message": "Failed to open loot box"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LootBoxInventoryView(APIView):
    """Get user's unopened loot boxes"""
    permission_classes = (IsValidated,)

    def get(self, request):
        """Get user's loot box inventory (unopened boxes)"""
        try:
            inventory = LootBoxService.get_user_loot_box_inventory(request.user)

            return CommonUtils.dispatch_success({
                'inventory': inventory,
                'total_unopened': sum(item['quantity_remaining'] for item in inventory),
                'message': 'Loot box inventory retrieved successfully'
            })
        except Exception as e:
            logger.error(f"Error fetching loot box inventory: {e}")
            return Response({
                "status": "error",
                "message": "Failed to fetch loot box inventory"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LootBoxPurchaseHistoryView(APIView):
    """Get user's loot box purchase history"""
    permission_classes = (IsValidated,)

    def get(self, request):
        """Get user's complete purchase history"""
        try:
            history = LootBoxService.get_user_purchase_history(request.user)

            # Calculate statistics
            total_purchased = sum(item['quantity_purchased'] for item in history)
            total_opened = sum(item['quantity_opened'] for item in history)
            total_spent = sum(item['total_cost'] for item in history)

            return CommonUtils.dispatch_success({
                'purchase_history': history,
                'statistics': {
                    'total_purchases': len(history),
                    'total_boxes_purchased': total_purchased,
                    'total_boxes_opened': total_opened,
                    'total_food_items_spent': total_spent,
                },
                'message': 'Purchase history retrieved successfully'
            })
        except Exception as e:
            logger.error(f"Error fetching purchase history: {e}")
            return Response({
                "status": "error",
                "message": "Failed to fetch purchase history"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LootBoxRewardHistoryView(APIView):
    """Get user's loot box reward history"""
    permission_classes = (IsValidated,)

    def get(self, request):
        """Get user's complete reward history"""
        try:
            history = LootBoxService.get_user_reward_history(request.user)

            # Calculate statistics by rarity
            rarity_stats = {
                'COMMON': 0,
                'RARE': 0,
                'EPIC': 0,
                'LEGENDARY': 0,
            }
            total_rewards_value = 0

            for reward in history:
                rarity = reward['reward']['rarity']
                if rarity in rarity_stats:
                    rarity_stats[rarity] += 1
                total_rewards_value += reward['reward']['total_points_value']

            return CommonUtils.dispatch_success({
                'reward_history': history,
                'statistics': {
                    'total_boxes_opened': len(history),
                    'rarity_breakdown': rarity_stats,
                    'total_points_value': total_rewards_value,
                },
                'message': 'Reward history retrieved successfully'
            })
        except Exception as e:
            logger.error(f"Error fetching reward history: {e}")
            return Response({
                "status": "error",
                "message": "Failed to fetch reward history"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@permission_classes([IsValidated])
def account_nft_update(request):

    tx_hash = request.data.get("tx_hash")  # DRF-friendly (json/form)
    if tx_hash:
        MintProfile.objects.update_or_create(
            user=request.user,
            defaults={
                "tx_hash": tx_hash,
                "contract_address": EnvironmentVariable.ACCOUNT_NFT_COLLECTION_ADDRESS,
            },
        )
    nft_sync()
    return Response(
        UserLookupSerializer(request.user).data,
        status=status.HTTP_200_OK,
    )
