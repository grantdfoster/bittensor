# The MIT License (MIT)
# Copyright © 2024 Opentensor Foundation
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the “Software”), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of
# the Software.
#
# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

from time import sleep
from typing import List, Union, Optional

from bittensor_wallet import Wallet
from rich.prompt import Confirm

from bittensor.core.errors import NotRegisteredError, StakeError
from bittensor.core.settings import bt_console
from bittensor.utils.balance import Balance


def __do_remove_stake_single(
    subtensor,
    wallet: "Wallet",
    hotkey_ss58: str,
    amount: "Balance",
    wait_for_inclusion: bool = True,
    wait_for_finalization: bool = False,
) -> bool:
    r"""
    Executes an unstake call to the chain using the wallet and the amount specified.

    Args:
        wallet (Wallet):
            Bittensor wallet object.
        hotkey_ss58 (str):
            Hotkey address to unstake from.
        amount (bittensor.Balance):
            Amount to unstake as Bittensor balance object.
        wait_for_inclusion (bool):
            If set, waits for the extrinsic to enter a block before returning ``true``, or returns ``false`` if the extrinsic fails to enter the block within the timeout.
        wait_for_finalization (bool):
            If set, waits for the extrinsic to be finalized on the chain before returning ``true``, or returns ``false`` if the extrinsic fails to be finalized within the timeout.
        prompt (bool):
            If ``true``, the call waits for confirmation from the user before proceeding.
    Returns:
        success (bool):
            Flag is ``true`` if extrinsic was finalized or uncluded in the block. If we did not wait for finalization / inclusion, the response is ``true``.
    Raises:
        bittensor.core.errors.StakeError:
            If the extrinsic fails to be finalized or included in the block.
        bittensor.core.errors.NotRegisteredError:
            If the hotkey is not registered in any subnets.

    """
    # Decrypt keys,
    wallet.coldkey

    success = subtensor._do_unstake(
        wallet=wallet,
        hotkey_ss58=hotkey_ss58,
        amount=amount,
        wait_for_inclusion=wait_for_inclusion,
        wait_for_finalization=wait_for_finalization,
    )

    return success


def check_threshold_amount(
    subtensor, stake_balance: Balance
) -> bool:
    """
    Checks if the remaining stake balance is above the minimum required stake threshold.

    Args:
        stake_balance (Balance):
            the balance to check for threshold limits.

    Returns:
        success (bool):
            ``true`` if the unstaking is above the threshold or 0, or ``false`` if the
                unstaking is below the threshold, but not 0.
    """
    min_req_stake: Balance = subtensor.get_minimum_required_stake()

    if min_req_stake > stake_balance > 0:
        bt_console.print(
            f":cross_mark: [yellow]Remaining stake balance of {stake_balance} less than minimum of {min_req_stake} TAO[/yellow]"
        )
        return False
    else:
        return True


def unstake_extrinsic(
    subtensor,
    wallet: "Wallet",
    hotkey_ss58: Optional[str] = None,
    amount: Optional[Union[Balance, float]] = None,
    wait_for_inclusion: bool = True,
    wait_for_finalization: bool = False,
    prompt: bool = False,
) -> bool:
    r"""Removes stake into the wallet coldkey from the specified hotkey ``uid``.

    Args:
        wallet (Wallet):
            Bittensor wallet object.
        hotkey_ss58 (Optional[str]):
            The ``ss58`` address of the hotkey to unstake from. By default, the wallet hotkey is used.
        amount (Union[Balance, float]):
            Amount to stake as Bittensor balance, or ``float`` interpreted as Tao.
        wait_for_inclusion (bool):
            If set, waits for the extrinsic to enter a block before returning ``true``, or returns ``false`` if the extrinsic fails to enter the block within the timeout.
        wait_for_finalization (bool):
            If set, waits for the extrinsic to be finalized on the chain before returning ``true``, or returns ``false`` if the extrinsic fails to be finalized within the timeout.
        prompt (bool):
            If ``true``, the call waits for confirmation from the user before proceeding.
    Returns:
        success (bool):
            Flag is ``true`` if extrinsic was finalized or uncluded in the block. If we did not wait for finalization / inclusion, the response is ``true``.
    """
    # Decrypt keys,
    wallet.coldkey

    if hotkey_ss58 is None:
        hotkey_ss58 = wallet.hotkey.ss58_address  # Default to wallet's own hotkey.

    with bt_console.status(
        ":satellite: Syncing with chain: [white]{}[/white] ...".format(
            subtensor.network
        )
    ):
        old_balance = subtensor.get_balance(wallet.coldkeypub.ss58_address)
        old_stake = subtensor.get_stake_for_coldkey_and_hotkey(
            coldkey_ss58=wallet.coldkeypub.ss58_address, hotkey_ss58=hotkey_ss58
        )

        hotkey_owner = subtensor.get_hotkey_owner(hotkey_ss58)
        own_hotkey: bool = wallet.coldkeypub.ss58_address == hotkey_owner

    # Convert to bittensor.Balance
    if amount is None:
        # Unstake it all.
        unstaking_balance = old_stake
    elif not isinstance(amount, Balance):
        unstaking_balance = Balance.from_tao(amount)
    else:
        unstaking_balance = amount

    # Check enough to unstake.
    stake_on_uid = old_stake
    if unstaking_balance > stake_on_uid:
        bt_console.print(
            ":cross_mark: [red]Not enough stake[/red]: [green]{}[/green] to unstake: [blue]{}[/blue] from hotkey: [white]{}[/white]".format(
                stake_on_uid, unstaking_balance, wallet.hotkey_str
            )
        )
        return False

    # If nomination stake, check threshold.
    if not own_hotkey and not check_threshold_amount(
        subtensor=subtensor, stake_balance=(stake_on_uid - unstaking_balance)
    ):
        bt_console.print(
            f":warning: [yellow]This action will unstake the entire staked balance![/yellow]"
        )
        unstaking_balance = stake_on_uid

    # Ask before moving on.
    if prompt:
        if not Confirm.ask(
            "Do you want to unstake:\n[bold white]  amount: {}\n  hotkey: {}[/bold white ]?".format(
                unstaking_balance, wallet.hotkey_str
            )
        ):
            return False

    try:
        with bt_console.status(
            ":satellite: Unstaking from chain: [white]{}[/white] ...".format(
                subtensor.network
            )
        ):
            staking_response: bool = __do_remove_stake_single(
                subtensor=subtensor,
                wallet=wallet,
                hotkey_ss58=hotkey_ss58,
                amount=unstaking_balance,
                wait_for_inclusion=wait_for_inclusion,
                wait_for_finalization=wait_for_finalization,
            )

        if staking_response is True:  # If we successfully unstaked.
            # We only wait here if we expect finalization.
            if not wait_for_finalization and not wait_for_inclusion:
                return True

            bt_console.print(
                ":white_heavy_check_mark: [green]Finalized[/green]"
            )
            with bt_console.status(
                ":satellite: Checking Balance on: [white]{}[/white] ...".format(
                    subtensor.network
                )
            ):
                new_balance = subtensor.get_balance(
                    address=wallet.coldkeypub.ss58_address
                )
                new_stake = subtensor.get_stake_for_coldkey_and_hotkey(
                    coldkey_ss58=wallet.coldkeypub.ss58_address, hotkey_ss58=hotkey_ss58
                )  # Get stake on hotkey.
                bt_console.print(
                    "Balance:\n  [blue]{}[/blue] :arrow_right: [green]{}[/green]".format(
                        old_balance, new_balance
                    )
                )
                bt_console.print(
                    "Stake:\n  [blue]{}[/blue] :arrow_right: [green]{}[/green]".format(
                        old_stake, new_stake
                    )
                )
                return True
        else:
            bt_console.print(
                ":cross_mark: [red]Failed[/red]: Unknown Error."
            )
            return False

    except NotRegisteredError as e:
        bt_console.print(
            ":cross_mark: [red]Hotkey: {} is not registered.[/red]".format(
                wallet.hotkey_str
            )
        )
        return False
    except StakeError as e:
        bt_console.print(":cross_mark: [red]Stake Error: {}[/red]".format(e))
        return False


def unstake_multiple_extrinsic(
    subtensor,
    wallet: "Wallet",
    hotkey_ss58s: List[str],
    amounts: Optional[List[Union[Balance, float]]] = None,
    wait_for_inclusion: bool = True,
    wait_for_finalization: bool = False,
    prompt: bool = False,
) -> bool:
    r"""Removes stake from each ``hotkey_ss58`` in the list, using each amount, to a common coldkey.

    Args:
        wallet (Wallet):
            The wallet with the coldkey to unstake to.
        hotkey_ss58s (List[str]):
            List of hotkeys to unstake from.
        amounts (List[Union[Balance, float]]):
            List of amounts to unstake. If ``None``, unstake all.
        wait_for_inclusion (bool):
            If set, waits for the extrinsic to enter a block before returning ``true``, or returns ``false`` if the extrinsic fails to enter the block within the timeout.
        wait_for_finalization (bool):
            If set, waits for the extrinsic to be finalized on the chain before returning ``true``, or returns ``false`` if the extrinsic fails to be finalized within the timeout.
        prompt (bool):
            If ``true``, the call waits for confirmation from the user before proceeding.
    Returns:
        success (bool):
            Flag is ``true`` if extrinsic was finalized or included in the block. Flag is ``true`` if any wallet was unstaked. If we did not wait for finalization / inclusion, the response is ``true``.
    """
    if not isinstance(hotkey_ss58s, list) or not all(
        isinstance(hotkey_ss58, str) for hotkey_ss58 in hotkey_ss58s
    ):
        raise TypeError("hotkey_ss58s must be a list of str")

    if len(hotkey_ss58s) == 0:
        return True

    if amounts is not None and len(amounts) != len(hotkey_ss58s):
        raise ValueError("amounts must be a list of the same length as hotkey_ss58s")

    if amounts is not None and not all(
        isinstance(amount, (Balance, float)) for amount in amounts
    ):
        raise TypeError(
            "amounts must be a [list of Balance or float] or None"
        )

    if amounts is None:
        amounts = [None] * len(hotkey_ss58s)
    else:
        # Convert to Balance
        amounts = [
            Balance.from_tao(amount) if isinstance(amount, float) else amount
            for amount in amounts
        ]

        if sum(amount.tao for amount in amounts) == 0:
            # Staking 0 tao
            return True

    # Unlock coldkey.
    wallet.coldkey

    old_stakes = []
    own_hotkeys = []
    with bt_console.status(
        ":satellite: Syncing with chain: [white]{}[/white] ...".format(
            subtensor.network
        )
    ):
        old_balance = subtensor.get_balance(wallet.coldkeypub.ss58_address)

        for hotkey_ss58 in hotkey_ss58s:
            old_stake = subtensor.get_stake_for_coldkey_and_hotkey(
                coldkey_ss58=wallet.coldkeypub.ss58_address, hotkey_ss58=hotkey_ss58
            )  # Get stake on hotkey.
            old_stakes.append(old_stake)  # None if not registered.

            hotkey_owner = subtensor.get_hotkey_owner(hotkey_ss58)
            own_hotkeys.append(wallet.coldkeypub.ss58_address == hotkey_owner)

    successful_unstakes = 0
    for idx, (hotkey_ss58, amount, old_stake, own_hotkey) in enumerate(
        zip(hotkey_ss58s, amounts, old_stakes, own_hotkeys)
    ):
        # Covert to bittensor.Balance
        if amount is None:
            # Unstake it all.
            unstaking_balance = old_stake
        elif not isinstance(amount, Balance):
            unstaking_balance = Balance.from_tao(amount)
        else:
            unstaking_balance = amount

        # Check enough to unstake.
        stake_on_uid = old_stake
        if unstaking_balance > stake_on_uid:
            bt_console.print(
                ":cross_mark: [red]Not enough stake[/red]: [green]{}[/green] to unstake: [blue]{}[/blue] from hotkey: [white]{}[/white]".format(
                    stake_on_uid, unstaking_balance, wallet.hotkey_str
                )
            )
            continue

        # If nomination stake, check threshold.
        if not own_hotkey and not check_threshold_amount(
            subtensor=subtensor, stake_balance=(stake_on_uid - unstaking_balance)
        ):
            bt_console.print(
                f":warning: [yellow]This action will unstake the entire staked balance![/yellow]"
            )
            unstaking_balance = stake_on_uid

        # Ask before moving on.
        if prompt:
            if not Confirm.ask(
                "Do you want to unstake:\n[bold white]  amount: {}\n  hotkey: {}[/bold white ]?".format(
                    unstaking_balance, wallet.hotkey_str
                )
            ):
                continue

        try:
            with bt_console.status(
                ":satellite: Unstaking from chain: [white]{}[/white] ...".format(
                    subtensor.network
                )
            ):
                staking_response: bool = __do_remove_stake_single(
                    subtensor=subtensor,
                    wallet=wallet,
                    hotkey_ss58=hotkey_ss58,
                    amount=unstaking_balance,
                    wait_for_inclusion=wait_for_inclusion,
                    wait_for_finalization=wait_for_finalization,
                )

            if staking_response is True:  # If we successfully unstaked.
                # We only wait here if we expect finalization.

                if idx < len(hotkey_ss58s) - 1:
                    # Wait for tx rate limit.
                    tx_rate_limit_blocks = subtensor.tx_rate_limit()
                    if tx_rate_limit_blocks > 0:
                        bt_console.print(
                            ":hourglass: [yellow]Waiting for tx rate limit: [white]{}[/white] blocks[/yellow]".format(
                                tx_rate_limit_blocks
                            )
                        )
                        sleep(tx_rate_limit_blocks * 12)  # 12 seconds per block

                if not wait_for_finalization and not wait_for_inclusion:
                    successful_unstakes += 1
                    continue

                bt_console.print(
                    ":white_heavy_check_mark: [green]Finalized[/green]"
                )
                with bt_console.status(
                    ":satellite: Checking Balance on: [white]{}[/white] ...".format(
                        subtensor.network
                    )
                ):
                    block = subtensor.get_current_block()
                    new_stake = subtensor.get_stake_for_coldkey_and_hotkey(
                        coldkey_ss58=wallet.coldkeypub.ss58_address,
                        hotkey_ss58=hotkey_ss58,
                        block=block,
                    )
                    bt_console.print(
                        "Stake ({}): [blue]{}[/blue] :arrow_right: [green]{}[/green]".format(
                            hotkey_ss58, stake_on_uid, new_stake
                        )
                    )
                    successful_unstakes += 1
            else:
                bt_console.print(
                    ":cross_mark: [red]Failed[/red]: Unknown Error."
                )
                continue

        except NotRegisteredError as e:
            bt_console.print(
                ":cross_mark: [red]{} is not registered.[/red]".format(hotkey_ss58)
            )
            continue
        except StakeError as e:
            bt_console.print(
                ":cross_mark: [red]Stake Error: {}[/red]".format(e)
            )
            continue

    if successful_unstakes != 0:
        with bt_console.status(
            ":satellite: Checking Balance on: ([white]{}[/white] ...".format(
                subtensor.network
            )
        ):
            new_balance = subtensor.get_balance(wallet.coldkeypub.ss58_address)
        bt_console.print(
            "Balance: [blue]{}[/blue] :arrow_right: [green]{}[/green]".format(
                old_balance, new_balance
            )
        )
        return True

    return False
