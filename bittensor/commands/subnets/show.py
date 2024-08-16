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

import sys
import argparse
from typing import TYPE_CHECKING

from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt

from bittensor import Balance
from bittensor import __console__ as console
from bittensor.btlogging import logging
from bittensor.chain_data import SubnetState
from bittensor.config import config as Config
from bittensor.subtensor import Subtensor

if TYPE_CHECKING:
    from bittensor.cli import cli as Cli


class ShowSubnet:

    @classmethod
    def add_args(cls, parser: argparse.ArgumentParser):
        stake_parser = parser.add_parser("show", help="""Show Subnet Stake.""")
        stake_parser.add_argument("--netuid", dest="netuid", type=int, required=False)
        stake_parser.add_argument("--no_prompt", "--y", "-y", dest='no_prompt', required=False, action='store_true', help="""Specify this flag to delegate stake""")
        Subtensor.add_args(stake_parser)
        
    @staticmethod
    def check_config(config: "Config"): pass
    
    @staticmethod
    def run(cli: "Cli"):
        config = cli.config.copy()
        subtensor = Subtensor(config=config, log_verbose=False)
        
        # Get netuid
        netuid = config.get('netuid') 
        if config.is_set("netuid"):
            netuid = config.get('netuid')
        elif not config.no_prompt:
            netuid = int( Prompt.ask("Enter netuid", default="0") )
        else:
            logging.error("netuid is needed to proceed")
            sys.exit(1)
            
        
        subnet_info = subtensor.get_subnet_dynamic_info(netuid)
        subnet_state: "SubnetState" = SubnetState.from_vec_u8(
            subtensor.substrate.rpc_request(method="subnetInfo_getSubnetState", params=[netuid, None])['result']
        )
        # Define table properties
        console_width = console.width - 5

        table = Table(
            title=f"[white]Subnet State #{config.netuid}",
            width=console_width,
            safe_box=True,
            padding=(0, 1),
            collapse_padding=False,
            pad_edge=True,
            expand=True,
            show_header=True,
            show_footer=True,
            show_edge=False,
            show_lines=False,
            leading=0,
            style="none",
            row_styles=None,
            header_style="bold",
            footer_style="bold",
            border_style="rgb(7,54,66)",
            title_style="bold magenta",
            title_justify="center",
            highlight=False,
        )
        subnet_info_table = Table(
            width=console_width,
            safe_box=True,
            padding=(0, 1),
            collapse_padding=False,
            pad_edge=True,
            expand=True,
            show_header=True,
            show_footer=False,
            show_edge=False,
            show_lines=False,
            leading=0,
            style="none",
            row_styles=None,
            header_style="bold",
            footer_style="bold",
            border_style="rgb(7,54,66)",
            title_style="bold magenta",
            title_justify="center",
            highlight=False,
        )
        
        subnet_info_table.add_column("Index", style="rgb(253,246,227)", no_wrap=True, justify="center")
        subnet_info_table.add_column("Symbol", style="rgb(211,54,130)", no_wrap=True, justify="center")
        subnet_info_table.add_column(f"Emission ({Balance.get_unit(0)})", style="rgb(38,139,210)", no_wrap=True, justify="center")
        subnet_info_table.add_column(f"P({Balance.get_unit(0)},", style="rgb(108,113,196)", no_wrap=True, justify="right")
        subnet_info_table.add_column(f"{Balance.get_unit(1)})", style="rgb(42,161,152)", no_wrap=True, justify="left")
        subnet_info_table.add_column(f"{Balance.get_unit(1)}", style="rgb(133,153,0)", no_wrap=True, justify="center")
        subnet_info_table.add_column(f"Rate ({Balance.get_unit(1)}/{Balance.get_unit(0)})", style="rgb(181,137,0)", no_wrap=True, justify="center")
        subnet_info_table.add_column("Tempo", style="rgb(38,139,210)", no_wrap=True, justify="center")
        subnet_info_table.add_row(
            str(netuid),
            f"[light_goldenrod1]{str(subnet_info.symbol)}[light_goldenrod1]",
            f"τ{subnet_info.emission.tao:.4f}",
            f"P( τ{subnet_info.tao_in.tao:,.4f},",
            f"{subnet_info.alpha_in.tao:,.4f}{subnet_info.symbol} )",
            f"{subnet_info.alpha_out.tao:,.4f}{subnet_info.symbol}",
            f"{subnet_info.price.tao:.4f}τ/{subnet_info.symbol}",
            str(subnet_info.blocks_since_last_step) + "/" + str(subnet_info.tempo),
                # f"{subnet.owner_locked}" + "/" + f"{subnet.total_locked}",
                # f"{subnet.owner[:3]}...{subnet.owner[-3:]}",
        )

        # Add columns to the table
        table.add_column("uid", style="rgb(133,153,0)", no_wrap=True, justify="center")
        table.add_column(f"{Balance.get_unit(netuid)}", style="rgb(42,161,152)", no_wrap=True, justify="center")
        table.add_column(f"{Balance.get_unit(0)}", style="rgb(211,54,130)", no_wrap=True, justify="center")
        table.add_column("stake", style="rgb(108,113,196)", no_wrap=True, justify="center")
        table.add_column("dividends", style="rgb(181,137,0)", no_wrap=True, justify="center")
        table.add_column("incentive", style="rgb(220,50,47)", no_wrap=True, justify="center")
        table.add_column(f"emission ({Balance.get_unit(netuid)})", style="rgb(38,139,210)", no_wrap=True, justify="center")
        table.add_column("hotkey", style="rgb(42,161,152)", no_wrap=True, justify="center")
        # table.add_column("cold", style="rgb(133,153,0)", no_wrap=True, justify="center")
        # table.add_column("A", style="rgb(211,54,130)", no_wrap=True, justify="center")
        # table.add_column("V", style="rgb(211,54,130)", no_wrap=True, justify="center")
        # table.add_column("P", style="rgb(211,54,130)", no_wrap=True, justify="center")
        # table.add_column("U", style="rgb(211,54,130)", no_wrap=True, justify="center")
        # table.add_column("D", style="rgb(211,54,130)", no_wrap=True, justify="center")
        # table.add_column("I", style="rgb(211,54,130)", no_wrap=True, justify="center")
        # table.add_column("C", style="rgb(211,54,130)", no_wrap=True, justify="center")
        # table.add_column("T", style="rgb(211,54,130)", no_wrap=True, justify="center")
        # table.add_column("R", style="rgb(211,54,130)", no_wrap=True, justify="center")
        # table.add_column("Regist", style="rgb(211,54,130)", no_wrap=True, justify="center")

        for idx, hk in enumerate(subnet_state.hotkeys):
            table.add_row(
                str(idx),
                str(subnet_state.local_stake[idx]),
                str(subnet_state.global_stake[idx]),
                f"{subnet_state.stake_weight[idx]:.4f}",
                str(subnet_state.dividends[idx]),
                str(subnet_state.incentives[idx]),
                str(subnet_state.emission[idx]),
                f"{subnet_state.hotkeys[idx]}",
            
            )

        # Print the table
        import bittensor as bt
        bt.__console__.print("\n\n\n")
        bt.__console__.print(f"\t\tSubnet: {netuid}: Owner: {subnet_info.owner}, Total Locked: {subnet_info.total_locked}, Owner Locked: {subnet_info.owner_locked}")
        bt.__console__.print("\n\n\n")
        bt.__console__.print(subnet_info_table)
        bt.__console__.print("\n\n\n")
        bt.__console__.print(table)
