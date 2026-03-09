import json
import uuid

from django.db.models import Q
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import requests
from celery import shared_task
import logging

from django.db import transaction

from environment.variables import EnvironmentVariable
from user.models import UserLootBoxReward, MintProfile, User
from user.utils import w3, Web3, lootbox_contract, contract

logger = logging.getLogger(__name__)

PRIVATE_KEY = EnvironmentVariable.PRIVATE_KEY


def mint_nft(reward):
    account = w3.eth.account.from_key(PRIVATE_KEY)
    signer_address = Web3.to_checksum_address(account.address)
    nonce = w3.eth.get_transaction_count(signer_address, "pending")
    tx = lootbox_contract.functions.mintTo(
        Web3.to_checksum_address(reward.user.wallet_address),
        reward.token_meta_uri
    ).build_transaction({
        "from": EnvironmentVariable.LOOTBOX_NFT_OWNER,
        "nonce": nonce,
        "chainId": EnvironmentVariable.CHAIN_ID,
        "gas": 400000,  # adjust if needed
        "gasPrice": w3.eth.gas_price,
    })
    signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    try:
        raw_tx = signed_tx.rawTransaction
    except AttributeError:
        raw_tx = signed_tx.raw_transaction
    tx_hash = w3.eth.send_raw_transaction(raw_tx)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    if receipt.status != 1:
        raise Exception(f"Mint failed: {tx_hash.hex()}")

    if receipt.status == 1:
        return tx_hash.hex()
    return None


def upload_metadata_to_thirdweb(metadata):
    url = "https://storage.thirdweb.com/ipfs/upload"

    headers = {
        "x-secret-key": EnvironmentVariable.THIRDWEB_SECRET_ID
    }

    files = {
        "file": ("metadata.json", json.dumps(metadata), "application/json")
    }

    response = requests.post(url, headers=headers, files=files, timeout=30)

    response.raise_for_status()

    res = response.json()

    ipfs_hash = res.get("IpfsHash")

    if not ipfs_hash:
        raise ValueError(f"Invalid IPFS response {res}")

    return f"ipfs://{ipfs_hash}"


def process_reward_nft_sync(user_reward_id):
    try:
        reward = UserLootBoxReward.objects.select_related(
            "user",
            "loot_box",
            "loot_box_reward"
        ).get(id=user_reward_id)

        selected_reward = reward.loot_box_reward
        user = reward.user
        loot_box = reward.loot_box
        if not reward.token_meta_uri:
            metadata = {
                "name": selected_reward.title,
                "description": selected_reward.description or "",
                "image": selected_reward.image.url if selected_reward.image else "https://api-nft.macd.gg/static/lootbox.jpg",
                "attributes": [
                    {"trait_type": "Rarity", "value": selected_reward.rarity},
                    {"trait_type": "Winner", "value": user.username},
                    {"trait_type": "Lootbox Title", "value": loot_box.name},
                    {"trait_type": "uuid", "value": str(reward.id)},
                    {"trait_type": "Reward ID", "value": str(selected_reward.id)},
                    {"trait_type": "Lootbox ID", "value": str(loot_box.id)},
                ]
            }

            token_uri = upload_metadata_to_thirdweb(metadata)
            reward.token_meta_uri = token_uri
            reward.save(update_fields=["token_meta_uri"])
        if reward.status == 'user_win' or reward.status == 'error':
            tx_hash = mint_nft(reward)
            if tx_hash:
                reward.tx_hash = tx_hash
                reward.status = "mint_start"
                reward.contract_address = EnvironmentVariable.LOOTBOX_COLLECTION_ADDRESS

            reward.save(update_fields=["tx_hash", "status", "contract_address"])

    except Exception as e:

        logger.exception("NFT mint failed")

        UserLootBoxReward.objects.filter(id=user_reward_id).update(
            status="error"
        )


# @shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
# def process_reward_nft(self, user_reward_id):
#     return process_reward_nft_sync(user_reward_id)

_HTTP = requests.Session()
_retry = Retry(total=3, backoff_factor=0.3, status_forcelist=(429, 500, 502, 503, 504), allowed_methods=('GET',))
_adapter = HTTPAdapter(max_retries=_retry, pool_connections=20, pool_maxsize=20)
_HTTP.mount('http://', _adapter)
_HTTP.mount('https://', _adapter)


def resolve_nft_status(owner):
    if not owner or owner.lower() == EnvironmentVariable.ACCOUNT_NFT_OWNER.lower():
        return 'mint_done'
    return 'transfer_done'


def nft_sync(batch_size=50):
    """Sync NFTs from blockchain in batches (optimized)."""

    try:
        next_token_id = contract.functions.nextTokenIdToMint().call()
    except Exception as e:
        logger.error(f"[NFT_SYNC] Failed to fetch nextTokenIdToMint: {e}")
        return

    contract_addr = EnvironmentVariable.ACCOUNT_NFT_COLLECTION_ADDRESS

    # Get all existing token_ids in DB
    existing_ids = set(
        MintProfile.objects.filter(contract_address=contract_addr)
        .values_list("token_id", flat=True)
    )

    # Compute missing token_ids
    missing_ids = [i for i in range(next_token_id) if i not in existing_ids]

    if not missing_ids:
        logger.info("[NFT_SYNC] No missing tokens to sync")
        return

    # Process missing ids in batches
    for i in range(0, len(missing_ids), batch_size):
        batch_ids = missing_ids[i:i + batch_size]

        records = []

        for token_id in batch_ids:
            try:
                token_uri = contract.functions.tokenURI(token_id).call()
                url = token_uri.replace("ipfs://", "https://ipfs.io/ipfs/")
                metadata = get_url_data(url) or {}
            except Exception as e:
                logger.warning(f"[NFT_SYNC] Token {token_id}: metadata fetch failed: {e}")
                continue

            try:
                owner = contract.functions.ownerOf(token_id).call()
            except Exception as e:
                logger.warning(f"[NFT_SYNC] Token {token_id}: owner fetch failed: {e}")
                owner = None

            attrs = metadata.get("attributes")
            if isinstance(attrs, list):
                try:
                    metadata.update(
                        {a["trait_type"]: a["value"] for a in attrs if "trait_type" in a and "value" in a}
                    )
                except Exception:
                    pass

            user_id = metadata.get("user_id")
            wallet = metadata.get("wallet")

            try:
                user_uuid = uuid.UUID(str(user_id))
            except Exception:
                continue

            records.append(
                {
                    "token_id": token_id,
                    "token_uri": token_uri,
                    "owner": owner,
                    "metadata": metadata,
                    "user_uuid": str(user_uuid),
                    "wallet": wallet,
                }
            )

        if not records:
            continue

        # Resolve users
        user_ids = {r["user_uuid"] for r in records}
        wallets = {r["wallet"] for r in records if r.get("wallet")}

        users = list(
            User.objects.filter(Q(pk__in=user_ids) | Q(wallet_address__in=wallets))
            .only("id", "wallet_address")
        )

        users_by_id = {str(u.id): u for u in users}
        users_by_wallet = {u.wallet_address: u for u in users if u.wallet_address}

        resolved_users = []
        for r in records:
            u = users_by_id.get(r["user_uuid"]) or (
                users_by_wallet.get(r.get("wallet")) if r.get("wallet") else None
            )
            if u:
                resolved_users.append(u)

        resolved_users = list({u.id: u for u in resolved_users}.values())

        existing_profiles = {
            mp.user_id: mp
            for mp in MintProfile.objects.filter(
                contract_address=contract_addr,
                user__in=resolved_users,
            ).only(
                "id",
                "user_id",
                "metadata",
                "token_id",
                "token_meta_uri",
                "contract_address",
                "current_owner",
            )
        }

        to_create = []
        to_update = []

        for r in records:
            user = users_by_id.get(r["user_uuid"]) or (
                users_by_wallet.get(r.get("wallet")) if r.get("wallet") else None
            )
            if not user:
                continue

            mp = existing_profiles.get(user.id)

            if mp:
                mp.metadata = r["metadata"]
                mp.token_id = r["token_id"]
                mp.token_meta_uri = r["token_uri"]
                mp.contract_address = contract_addr
                mp.current_owner = r["owner"]
                to_update.append(mp)
            else:
                to_create.append(
                    MintProfile(
                        user=user,
                        metadata=r["metadata"],
                        token_id=r["token_id"],
                        token_meta_uri=r["token_uri"],
                        contract_address=contract_addr,
                        current_owner=r["owner"],
                    )
                )

        with transaction.atomic():
            if to_create:
                MintProfile.objects.bulk_create(to_create, ignore_conflicts=True)

            if to_update:
                MintProfile.objects.bulk_update(
                    to_update,
                    fields=[
                        "metadata",
                        "token_id",
                        "token_meta_uri",
                        "contract_address",
                        "current_owner",
                    ],
                )

        logger.info(
            f"[NFT_SYNC] Batch missing tokens {batch_ids[0]}-{batch_ids[-1]}: "
            f"created={len(to_create)} updated={len(to_update)}"
        )


def get_url_data(exact_url):
    headers = {"Content-Type": "application/json"}
    try:
        response = _HTTP.get(exact_url, headers=headers, timeout=(3, 10))  # timeout added
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.warning(f"Failed to fetch metadata from {exact_url}: {e}")
        return {}


def lootbox_nft_sync(batch_size=50):
    """Sync Lootbox NFTs from blockchain for missing token IDs (optimized)."""

    try:
        next_token_id = lootbox_contract.functions.nextTokenIdToMint().call()
    except Exception as e:
        logger.error(f"[NFT_SYNC] Failed to fetch nextTokenIdToMint: {e}")
        return

    contract_addr = EnvironmentVariable.LOOTBOX_COLLECTION_ADDRESS

    # All token_ids currently in DB for this contract
    existing_db_ids = set(
        UserLootBoxReward.objects.filter(contract_address=contract_addr)
        .values_list("token_id", flat=True)
    )

    # Compute missing token_ids in [0, next_token_id)
    missing_ids = [i for i in range(next_token_id) if i not in existing_db_ids]

    if not missing_ids:
        logger.info("[NFT_SYNC] No missing lootbox tokens to sync")
        return

    # Process missing ids in batches
    for i in range(0, len(missing_ids), batch_size):
        batch_ids = missing_ids[i: i + batch_size]

        # 1) Pull on-chain + metadata for missing token_ids (network bound)
        records = []
        for token_id in batch_ids:
            try:
                try:
                    token_uri = lootbox_contract.functions.tokenURI(token_id).call()
                    url = token_uri.replace("ipfs://", "https://ipfs.io/ipfs/")
                    metadata = get_url_data(url) or {}
                except Exception as e:
                    logger.warning(f"[NFT_SYNC] Token {token_id}: metadata fetch failed: {e}")
                    continue

                try:
                    owner = lootbox_contract.functions.ownerOf(token_id).call()
                except Exception as e:
                    logger.warning(f"[NFT_SYNC] Token {token_id}: owner fetch failed: {e}")
                    owner = None

                # Flatten attributes once
                attrs = metadata.get("attributes")
                if isinstance(attrs, list):
                    try:
                        metadata.update(
                            {a["trait_type"]: a["value"] for a in attrs if "trait_type" in a and "value" in a}
                        )
                    except Exception:
                        pass
                user_reward_id = metadata.get("uuid")

                # Validate UUID early
                try:
                    reward_uuid = uuid.UUID(str(user_reward_id))
                    print(reward_uuid)
                except Exception:
                    continue

                records.append(
                    {
                        "token_id": token_id,
                        "token_uri": token_uri,
                        "owner": owner,
                        "metadata": metadata,
                        "reward_uuid": str(reward_uuid),
                    }
                )
            except Exception as e:
                continue

        if not records:
            continue

        # 2) Resolve reward rows in ONE query
        reward_ids = [r["reward_uuid"] for r in records]
        print(reward_ids)
        existing_profiles = {
            str(mp.id): mp
            for mp in UserLootBoxReward.objects.filter(
                contract_address=contract_addr,
                id__in=reward_ids,
            ).only(
                "id",
                "metadata",
                "token_id",
                "token_meta_uri",
                "contract_address",
                "current_owner",
            )
        }
        print(existing_profiles)
        to_update = []

        # 3) Build updates (no DB writes in loop)
        for r in records:
            mp = existing_profiles.get(r["reward_uuid"])
            if not mp:
                continue

            mp.metadata = r["metadata"]
            mp.token_id = r["token_id"]
            mp.token_meta_uri = r["token_uri"]
            mp.contract_address = contract_addr
            mp.current_owner = r["owner"]
            mp.status = 'transfer_done'
            to_update.append(mp)

        # 4) Apply in bulk
        with transaction.atomic():
            if to_update:
                UserLootBoxReward.objects.bulk_update(
                    to_update,
                    fields=["metadata", "token_id", "token_meta_uri", "contract_address", "current_owner", "status"],
                )

        logger.info(
            f"[NFT_SYNC] Lootbox missing batch {batch_ids[0]}-{batch_ids[-1]}: updated={len(to_update)}"
        )


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=2)
def update_lootbox_nft(self):
    return lootbox_nft_sync()
