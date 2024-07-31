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

from unittest.mock import MagicMock, patch

import pytest
from bittensor_wallet import Wallet

from bittensor.api.extrinsics.network import (
    set_hyperparameter_extrinsic,
    register_subnetwork_extrinsic,
)
from bittensor.core.subtensor import Subtensor


# Mock the bittensor and related modules to avoid real network calls and wallet operations
@pytest.fixture
def mock_subtensor():
    subtensor = MagicMock(spec=Subtensor)
    subtensor.get_balance.return_value = 100
    subtensor.get_subnet_burn_cost.return_value = 10
    subtensor.substrate = MagicMock()
    subtensor.substrate.get_block_hash = MagicMock(return_value="0x" + "0" * 64)
    return subtensor


@pytest.fixture
def mock_wallet():
    wallet = MagicMock(spec=Wallet)
    wallet.coldkeypub.ss58_address = "fake_address"
    wallet.coldkey = MagicMock()
    return wallet


@pytest.fixture
def mock_other_owner_wallet():
    wallet = MagicMock(spec=Wallet)
    wallet.coldkeypub.ss58_address = "fake_other_owner"
    return wallet


@pytest.mark.parametrize(
    "test_id, wait_for_inclusion, wait_for_finalization, prompt, expected",
    [
        ("happy-path-01", False, True, False, True),
        ("happy-path-02", True, False, False, True),
        ("happy-path-03", False, False, False, True),
        ("happy-path-04", True, True, False, True),
    ],
)
def test_register_subnetwork_extrinsic_happy_path(
    mock_subtensor,
    mock_wallet,
    test_id,
    wait_for_inclusion,
    wait_for_finalization,
    prompt,
    expected,
):
    # Arrange
    mock_subtensor.substrate.submit_extrinsic.return_value.is_success = True

    # Act
    result = register_subnetwork_extrinsic(
        mock_subtensor, mock_wallet, wait_for_inclusion, wait_for_finalization, prompt
    )

    # Assert
    assert result == expected


# Edge cases
@pytest.mark.parametrize(
    "test_id, balance, burn_cost, prompt_input, expected",
    [
        ("edge-case-01", 0, 10, False, False),  # Balance is zero
        ("edge-case-02", 10, 10, False, False),  # Balance equals burn cost
        ("edge-case-03", 9, 10, False, False),  # Balance less than burn cost
        ("edge-case-04", 100, 10, True, True),  # User declines prompt
    ],
)
def test_register_subnetwork_extrinsic_edge_cases(
    mock_subtensor,
    mock_wallet,
    test_id,
    balance,
    burn_cost,
    prompt_input,
    expected,
    monkeypatch,
):
    # Arrange
    mock_subtensor.get_balance.return_value = balance
    mock_subtensor.get_subnet_burn_cost.return_value = burn_cost
    monkeypatch.setattr("rich.prompt.Confirm.ask", lambda x: prompt_input)

    # Act
    result = register_subnetwork_extrinsic(mock_subtensor, mock_wallet, prompt=True)

    # Assert
    assert result == expected


@pytest.mark.parametrize(
    "netuid, parameter, value, is_owner, wait_for_inclusion, wait_for_finalization, prompt, extrinsic_success, expected_result",
    [
        # Success - no wait
        (1, "serving_rate_limit", 49, True, False, False, False, True, True),
        # Success - with wait
        (1, "serving_rate_limit", 50, True, True, True, False, True, True),
        # Failure - wallet doesn't own subnet
        (1, "serving_rate_limit", 50, False, True, True, False, True, False),
        # Failure - invalid hyperparameter
        (1, None, 50, True, True, False, False, False, False),
    ],
    ids=[
        "success-no-wait",
        "success-with-wait",
        "failure-not-owner",
        "failure-invalid-hyperparameter",
    ],
)
def test_set_hyperparameter_extrinsic(
    mock_subtensor,
    mock_wallet,
    mock_other_owner_wallet,
    netuid,
    parameter,
    value,
    is_owner,
    wait_for_inclusion,
    wait_for_finalization,
    prompt,
    extrinsic_success,
    expected_result,
):
    # Arrange
    with patch.object(
        mock_subtensor,
        "get_subnet_owner",
        return_value=mock_wallet.coldkeypub.ss58_address
        if is_owner
        else mock_other_owner_wallet.coldkeypub.ss58_address,
    ), patch.object(
        mock_subtensor.substrate,
        "submit_extrinsic",
        return_value=MagicMock(is_success=extrinsic_success),
    ):
        # Act
        result = set_hyperparameter_extrinsic(
            subtensor=mock_subtensor,
            wallet=mock_wallet,
            netuid=netuid,
            parameter=parameter,
            value=value,
            wait_for_inclusion=wait_for_inclusion,
            wait_for_finalization=wait_for_finalization,
            prompt=prompt,
        )

        # Assert
        assert result == expected_result
