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
import bittensor as bt
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
            
        if netuid == 0:
            ShowSubnet.show_root(subtensor, config)
        else:
            ShowSubnet.show_subnet(subtensor, netuid, config)
            
    @staticmethod
    def show_root( subtensor: "Subtensor", config: "Config"):
        all_subnets = subtensor.get_all_subnet_dynamic_info()
        root_state: "SubnetState" = SubnetState.from_vec_u8(
            subtensor.substrate.rpc_request(method="subnetInfo_getSubnetState", params=[0, None])['result']
        )
        import bittensor as bt
        if root_state is None:
            bt.__console__.print(f"The root subnet does not exist")
            return
        if len(root_state.hotkeys) == 0:
            bt.__console__.print(f"The root-subnet is currently empty with 0 UIDs registered.")
            return

        console_width = console.width - 5
        table = Table(
            title=f"[white]Root Network",
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
        # Add columns to the table
        table.add_column("Position", style="rgb(253,246,227)", no_wrap=True, justify="center")
        table.add_column(f"Stake ({Balance.get_unit(0)})", style="dark_sea_green", no_wrap=True, justify="center")
        table.add_column(f"Stake ({Balance.get_unit(0)})", style="medium_purple", no_wrap=True, justify="center")
        table.add_column(f"Emission ({Balance.get_unit(0)}/block)", style="rgb(42,161,152)", no_wrap=True, justify="center")
        table.add_column("Hotkey", style="light_salmon3", no_wrap=True, justify="center")
        sorted_hotkeys = sorted(
            enumerate(root_state.hotkeys),
            key=lambda x: root_state.global_stake[x[0]],
            reverse=True
        )        
        for pos, (idx, hk) in enumerate(sorted_hotkeys):
            total_emission_per_block = 0
            for netuid in range( len(all_subnets)):
                subnet = all_subnets[netuid]
                emission_on_subnet = root_state.emission_history[netuid][idx] / subnet.tempo 
                total_emission_per_block += subnet.alpha_to_tao( Balance.from_rao(emission_on_subnet) )
            table.add_row(
                str((pos + 1)),
                str(root_state.local_stake[idx]),
                str(root_state.global_stake[idx]),
                str(total_emission_per_block),
                f"{root_state.hotkeys[idx]}",
            )

        # Print the table
        import bittensor as bt
        bt.__console__.print(table)
          
    @staticmethod
    def show_subnet(subtensor: "Subtensor", netuid: int, config: "Config"):

        subnet_info = subtensor.get_subnet_dynamic_info(netuid)
        subnet_state: "SubnetState" = SubnetState.from_vec_u8(
            subtensor.substrate.rpc_request(method="subnetInfo_getSubnetState", params=[netuid, None])['result']
        )
        if subnet_info is None:
            bt.__console__.print(f"Subnet {netuid} does not exist")
            return
        if len(subnet_state.hotkeys) == 0:
            bt.__console__.print(f"Subnet {netuid} is currently empty with 0 UIDs registered.")
            return

        # Define table properties
        console_width = console.width - 5
        table = Table(
            title=f"[white]Subnet State #{netuid}",
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
        )

        rows = []
        emission_sum = sum([subnet_state.emission[idx].tao for idx in range(len(subnet_state.emission))])
        for idx, hk in enumerate(subnet_state.hotkeys):
            hotkey_block_emission = subnet_state.emission[idx].tao/emission_sum if emission_sum != 0 else 0
            rows.append((
                    str(idx),
                    str(subnet_state.global_stake[idx]),
                    str(subnet_state.local_stake[idx]),
                    f"{subnet_state.stake_weight[idx]:.4f}",
                    str(subnet_state.dividends[idx]),
                    str(subnet_state.incentives[idx]),
                    str(Balance.from_tao(hotkey_block_emission).set_unit(netuid)),
                    f"{subnet_state.hotkeys[idx]}",
                )
            )        
        # Add columns to the table
        table.add_column("uid", style="rgb(133,153,0)", no_wrap=True, justify="center")
        table.add_column(f"Stake({Balance.get_unit(0)})", style="medium_purple", no_wrap=True, justify="right")
        table.add_column(f"Stake({Balance.get_unit(netuid)})", style="dark_sea_green", no_wrap=True, justify="right")
        table.add_column(f"Stake({Balance.get_unit(0)}•{Balance.get_unit(netuid)})", style="rgb(108,113,196)", no_wrap=True, justify="center")
        table.add_column("dividends", style="rgb(181,137,0)", no_wrap=True, justify="center")
        table.add_column("incentive", style="rgb(220,50,47)", no_wrap=True, justify="center")
        table.add_column(f"emission ({Balance.get_unit(netuid)})", style="rgb(38,139,210)", no_wrap=True, justify="center")
        table.add_column("hotkey", style="rgb(42,161,152)", no_wrap=True, justify="center")
        for row in rows:
            table.add_row(*row)

        # Print the table
        bt.__console__.print("\n\n\n")
        bt.__console__.print(f"\t\tSubnet: {netuid}: Owner: {subnet_info.owner}, Total Locked: {subnet_info.total_locked}, Owner Locked: {subnet_info.owner_locked}")
        bt.__console__.print("\n\n\n")
        bt.__console__.print(subnet_info_table)
        bt.__console__.print("\n\n\n")
        bt.__console__.print(table)
