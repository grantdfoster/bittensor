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

from typing import Union, TYPE_CHECKING

from rich.prompt import Confirm

from bittensor.core.settings import bt_console, NETWORK_EXPLORER_MAP
from bittensor.utils import get_explorer_url_for_network
from bittensor.utils import is_valid_bittensor_address_or_public_key
from bittensor.utils.balance import Balance
from bittensor_wallet import Wallet

# For annotation purposes
if TYPE_CHECKING:
    from bittensor.core.subtensor import Subtensor


# Community uses this extrinsic directly and via `subtensor.transfer`
def transfer_extrinsic(
    subtensor: "Subtensor",
    wallet: "Wallet",
    dest: str,
    amount: Union[Balance, float],
    wait_for_inclusion: bool = True,
    wait_for_finalization: bool = False,
    keep_alive: bool = True,
    prompt: bool = False,
) -> bool:
    """Transfers funds from this wallet to the destination public key address.

    Args:
        subtensor (subtensor.core.subtensor.Subtensor): The Subtensor instance object.
        wallet (bittensor.wallet): Bittensor wallet object to make transfer from.
        dest (str, ss58_address or ed25519): Destination public key address of receiver.
        amount (Union[Balance, int]): Amount to stake as Bittensor balance, or ``float`` interpreted as Tao.
        wait_for_inclusion (bool): If set, waits for the extrinsic to enter a block before returning ``true``, or returns ``false`` if the extrinsic fails to enter the block within the timeout.
        wait_for_finalization (bool): If set, waits for the extrinsic to be finalized on the chain before returning ``true``, or returns ``false`` if the extrinsic fails to be finalized within the timeout.
        keep_alive (bool): If set, keeps the account alive by keeping the balance above the existential deposit.
        prompt (bool): If ``true``, the call waits for confirmation from the user before proceeding.

    Returns:
        success (bool): Flag is ``true`` if extrinsic was finalized or uncluded in the block. If we did not wait for finalization / inclusion, the response is ``true``.
    """
    # Validate destination address.
    if not is_valid_bittensor_address_or_public_key(dest):
        bt_console.print(
            f":cross_mark: [red]Invalid destination address[/red]:[bold white]\n  {dest}[/bold white]"
        )
        return False

    if isinstance(dest, bytes):
        # Convert bytes to hex string.
        dest = "0x" + dest.hex()

    # Unlock wallet coldkey.
    wallet.unlock_coldkey()

    # Convert to bittensor.Balance
    if not isinstance(amount, Balance):
        transfer_balance = Balance.from_tao(amount)
    else:
        transfer_balance = amount

    # Check balance.
    with bt_console.status(":satellite: Checking Balance..."):
        account_balance = subtensor.get_balance(wallet.coldkey.ss58_address)
        # check existential deposit.
        existential_deposit = subtensor.get_existential_deposit()

    with bt_console.status(":satellite: Transferring..."):
        fee = subtensor.get_transfer_fee(
            wallet=wallet, dest=dest, value=transfer_balance.rao
        )

    if not keep_alive:
        # Check if the transfer should keep_alive the account
        existential_deposit = Balance(0)

    # Check if we have enough balance.
    if account_balance < (transfer_balance + fee + existential_deposit):
        bt_console.print(
            ":cross_mark: [red]Not enough balance[/red]:[bold white]\n"
            f"  balance: {account_balance}\n"
            f"  amount: {transfer_balance}\n"
            f"  for fee: {fee}[/bold white]"
        )
        return False

    # Ask before moving on.
    if prompt:
        if not Confirm.ask(
            "Do you want to transfer:[bold white]\n"
            f"  amount: {transfer_balance}\n"
            f"  from: {wallet.name}:{wallet.coldkey.ss58_address}\n"
            f"  to: {dest}\n"
            f"  for fee: {fee}[/bold white]"
        ):
            return False

    with bt_console.status(":satellite: Transferring..."):
        success, block_hash, err_msg = subtensor.do_transfer(
            wallet,
            dest,
            transfer_balance,
            wait_for_finalization=wait_for_finalization,
            wait_for_inclusion=wait_for_inclusion,
        )

        if success:
            bt_console.print(":white_heavy_check_mark: [green]Finalized[/green]")
            bt_console.print(f"[green]Block Hash: {block_hash}[/green]")

            explorer_urls = get_explorer_url_for_network(
                subtensor.network, block_hash, NETWORK_EXPLORER_MAP
            )
            if explorer_urls != {} and explorer_urls:
                bt_console.print(
                    f"[green]Opentensor Explorer Link: {explorer_urls.get('opentensor')}[/green]"
                )
                bt_console.print(
                    f"[green]Taostats   Explorer Link: {explorer_urls.get('taostats')}[/green]"
                )
        else:
            bt_console.print(f":cross_mark: [red]Failed[/red]: {err_msg}")

    if success:
        with bt_console.status(":satellite: Checking Balance..."):
            new_balance = subtensor.get_balance(wallet.coldkey.ss58_address)
            bt_console.print(
                f"Balance:\n  [blue]{account_balance}[/blue] :arrow_right: [green]{new_balance}[/green]"
            )
            return True

    return False
