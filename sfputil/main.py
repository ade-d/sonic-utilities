#!/usr/bin/env python
#
# main.py
#
# Command-line utility for interacting with SFP transceivers within SONiC
#

try:
    import imp
    import os
    import sys

    import click
    from sonic_py_common import device_info, logger, multi_asic
    from tabulate import tabulate
except ImportError as e:
    raise ImportError("%s - required module not found" % str(e))

VERSION = '2.0'

SYSLOG_IDENTIFIER = "sfputil"

PLATFORM_SPECIFIC_MODULE_NAME = "sfputil"
PLATFORM_SPECIFIC_CLASS_NAME = "SfpUtil"

# Global platform-specific sfputil class instance
platform_sfputil = None
PLATFORM_JSON = 'platform.json'
PORT_CONFIG_INI = 'port_config.ini'


# Global logger instance
log = logger.Logger(SYSLOG_IDENTIFIER)


# ========================== Methods for printing ==========================


# Convert arraw of raw bytes into pretty-printed string
def raw_bytes_to_string_pretty(raw_bytes):
    hexstr = ""

    for i in range(0, len(raw_bytes)):
        if i > 0 and (i % 8) == 0:
            hexstr += " "

        if i > 0 and (i % 16) == 0:
            hexstr += "\n"

        hexstr += raw_bytes[i]
        hexstr += " "

    return hexstr


# Recursively convert dictionary into pretty-printed string
def dict_to_string_pretty(in_dict, indent=0):
    if len(in_dict) == 0:
        return ""

    key = sorted(in_dict)[0]
    val = in_dict[key]

    if isinstance(val, dict):
        output = "%s%s:\n" % ('\t' * indent, key) + dict_to_string_pretty(val, indent + 1)
    else:
        output = "%s%s: %s\n" % ('\t' * indent, key, val)

    return output + dict_to_string_pretty({i:in_dict[i] for i in in_dict if i != key}, indent)


# Recursively convert dictionary into comma-separated string of 'key:value'
def dict_to_string_comma_separated(in_dict, key_blacklist, elemprefix, first=True):
    if len(in_dict) == 0:
        return ""

    output = ""
    key = sorted(in_dict)[0]
    val = in_dict[key]

    if key in key_blacklist:
        return ""

    if not first:
        output += ","
    else:
        first = False

    if isinstance(val, dict):
        output += dict_to_string_comma_separated(val, key_blacklist, key + '.', True)
    else:
        elemname = elemprefix + key
        output += elemname + ':' + str(val)

    return output + dict_to_string_comma_separated(
        {i:in_dict[i] for i in in_dict if i != key},
        key_blacklist, elemprefix, first)


# =============== Getting and printing SFP data ===============


def get_sfp_eeprom_status_string(port, port_sfp_eeprom_status):
    if port_sfp_eeprom_status:
        return "%s: SFP EEPROM detected" % port
    else:
        return "%s: SFP EEPROM not detected" % port


# Returns,
#   port_num if physical
#   logical_port:port_num if logical port and is a ganged port
#   logical_port if logical and not ganged
#
def get_physical_port_name(logical_port, physical_port, ganged):
    if logical_port == physical_port:
        return logical_port
    elif ganged:
        return logical_port + ":%d (ganged)" % physical_port
    else:
        return logical_port


def logical_port_name_to_physical_port_list(port_name):
    if port_name.startswith("Ethernet"):
        if platform_sfputil.is_logical_port(port_name):
            return platform_sfputil.get_logical_to_physical(port_name)
        else:
            click.echo("Error: Invalid port '%s'" % port_name)
            return None
    else:
        return [int(port_name)]


def print_all_valid_port_values():
    click.echo("Valid values for port: %s\n" % str(platform_sfputil.logical))


# Returns multi-line string of pretty SFP port EEPROM data
def port_eeprom_data_string_pretty(logical_port_name, dump_dom):
    result = ""
    ganged = False
    i = 1

    physical_port_list = logical_port_name_to_physical_port_list(logical_port_name)
    if physical_port_list is None:
        click.echo("Error: No physical ports found for logical port '%s'" % logical_port_name)
        return ""

    if len(physical_port_list) > 1:
        ganged = True

    for physical_port in physical_port_list:
        port_name = get_physical_port_name(logical_port_name, i, ganged)
        if not platform_sfputil.get_presence(physical_port):
            eeprom_dict = None
        else:
            eeprom_dict = platform_sfputil.get_eeprom_dict(physical_port)

        if eeprom_dict is not None:
            eeprom_iface_dict = eeprom_dict.get('interface')
            iface_data_dict = eeprom_iface_dict.get('data')
            result += get_sfp_eeprom_status_string(port_name, True)
            result += "\n"
            result += dict_to_string_pretty(iface_data_dict, 1)

            if dump_dom:
                eeprom_dom_dict = eeprom_dict.get('dom')
                if eeprom_dom_dict is not None:
                    dom_data_dict = eeprom_dom_dict.get('data')
                    if dom_data_dict is not None:
                        result += dict_to_string_pretty(dom_data_dict, 1)
        else:
            result += get_sfp_eeprom_status_string(port_name, False)
            result += "\n"

        result += "\n"
        i += 1

        return result


# Returns single-line string of pretty SFP port EEPROM data
# Nested dictionary items are prefixed using dot-notation
def port_eeprom_data_string_pretty_oneline(logical_port_name,
                                           ifdata_blacklist,
                                           domdata_blacklist,
                                           dump_dom):
    result = ""
    ganged = False
    i = 1

    physical_port_list = logical_port_name_to_physical_port_list(logical_port_name)
    if physical_port_list is None:
        click.echo("Error: No physical ports found for logical port '%s'" % logical_port_name)
        return ""

    if len(physical_port_list) > 1:
        ganged = True

    for physical_port in physical_port_list:
        if not platform_sfputil.get_presence(physical_port):
            eeprom_dict = None
        else:
            eeprom_dict = platform_sfputil.get_eeprom_dict(physical_port)

        # Only print detected sfp ports for oneline
        if eeprom_dict is not None:
            eeprom_iface_dict = eeprom_dict.get('interface')
            iface_data_dict = eeprom_iface_dict.get('data')
            result += "port:%s," % get_physical_port_name(logical_port_name, i, ganged)
            result += dict_to_string_comma_separated(iface_data_dict, ifdata_blacklist, "")

            if dump_dom:
                eeprom_dom_dict = eeprom_dict.get('dom')
                if eeprom_dom_dict is not None:
                    dom_data_dict = eeprom_dom_dict.get('data')
                    if dom_data_dict is not None:
                        result += dict_to_string_comma_separated(
                            dom_data_dict, domdata_blacklist, "")

        result += "\n"
        i += 1

    return result


def port_eeprom_data_raw_string_pretty(logical_port_name):
    result = ""
    ganged = False
    i = 1

    physical_port_list = logical_port_name_to_physical_port_list(logical_port_name)
    if physical_port_list is None:
        click.echo("Error: No physical ports found for logical port '%s'" % logical_port_name)
        return ""

    if len(physical_port_list) > 1:
        ganged = True

    for physical_port in physical_port_list:
        port_name = get_physical_port_name(logical_port_name, i, ganged)
        if not platform_sfputil.get_presence(physical_port):
            eeprom_raw = None
        else:
            eeprom_raw = platform_sfputil.get_eeprom_raw(physical_port)

        if eeprom_raw is None:
            result += get_sfp_eeprom_status_string(port_name, False)
            result += "\n"
        else:
            result += get_sfp_eeprom_status_string(port_name, True)
            result += "\n"
            result += raw_bytes_to_string_pretty(eeprom_raw)

        result += "\n"
        i += 1

    return result


# ==================== Methods for initialization ====================


# Loads platform specific sfputil module from source
def load_platform_sfputil():
    global platform_sfputil

    # Load platform module from source
    platform_path, _ = device_info.get_paths_to_platform_and_hwsku_dirs()

    try:
        module_file = os.path.join(platform_path, "plugins", PLATFORM_SPECIFIC_MODULE_NAME + ".py")
        module = imp.load_source(PLATFORM_SPECIFIC_MODULE_NAME, module_file)
    except IOError as e:
        log.log_error("Failed to load platform module '%s': %s" % (PLATFORM_SPECIFIC_MODULE_NAME, str(e)), True)
        return -1

    try:
        platform_sfputil_class = getattr(module, PLATFORM_SPECIFIC_CLASS_NAME)
        platform_sfputil = platform_sfputil_class()
    except AttributeError as e:
        log.log_error("Failed to instantiate '%s' class: %s" % (PLATFORM_SPECIFIC_CLASS_NAME, str(e)), True)
        return -2

    return 0


# ==================== CLI commands and groups ====================


# This is our main entrypoint - the main 'sfputil' command
@click.group()
def cli():
    """sfputil - Command line utility for managing SFP transceivers"""

    if os.geteuid() != 0:
        click.echo("Root privileges are required for this operation")
        sys.exit(1)

    # Load platform-specific sfputil class
    err = load_platform_sfputil()
    if err != 0:
        sys.exit(2)

    # Load port info
    try:
        if multi_asic.is_multi_asic():
            # For multi ASIC platforms we pass DIR of port_config_file_path and the number of asics
            (platform_path, hwsku_path) = device_info.get_paths_to_platform_and_hwsku_dirs()

            # Load platform module from source
            platform_sfputil.read_all_porttab_mappings(hwsku_path, multi_asic.get_num_asics())
        else:
            # For single ASIC platforms we pass port_config_file_path and the asic_inst as 0
            port_config_file_path = device_info.get_path_to_port_config_file()
            platform_sfputil.read_porttab_mappings(port_config_file_path, 0)
    except Exception as e:
        log.log_error("Error reading port info (%s)" % str(e), True)
        sys.exit(3)


# 'show' subgroup
@cli.group()
def show():
    """Display status of SFP transceivers"""
    pass


# 'eeprom' subcommand
@show.command()
@click.option('-p', '--port', metavar='<port_name>', help="Display SFP EEPROM data for port <port_name> only")
@click.option('-d', '--dom', 'dump_dom', is_flag=True, help="Also display Digital Optical Monitoring (DOM) data")
@click.option('-o', '--oneline', is_flag=True, help="Condense output for each port to a single line")
@click.option('--raw', is_flag=True, help="Output raw, unformatted data")
def eeprom(port, dump_dom, oneline, raw):
    """Display EEPROM data of SFP transceiver(s)"""
    logical_port_list = []
    output = ""

    # Create a list containing the logical port names of all ports we're interested in
    if port is None:
        logical_port_list = platform_sfputil.logical
    else:
        if platform_sfputil.is_valid_sfputil_port(port) == 0:
            click.echo("Error: invalid port '%s'\n" % port)
            print_all_valid_port_values()
            sys.exit(4)

        logical_port_list = [port]

    if raw:
        for logical_port_name in logical_port_list:
            output += port_eeprom_data_raw_string_pretty(logical_port_name)
            output += "\n"
    elif oneline:
        ifdata_out_blacklist = ["EncodingCodes",
                                "ExtIdentOfTypeOfTransceiver",
                                "NominalSignallingRate(UnitsOf100Mbd)"]
        domdata_out_blacklist = ["AwThresholds", "StatusControl"]

        for logical_port_name in logical_port_list:
            output += port_eeprom_data_string_pretty_oneline(logical_port_name,
                                                             ifdata_out_blacklist,
                                                             domdata_out_blacklist,
                                                             dump_dom)
    else:
        for logical_port_name in logical_port_list:
            output += port_eeprom_data_string_pretty(logical_port_name, dump_dom)

    click.echo(output)


# 'presence' subcommand
@show.command()
@click.option('-p', '--port', metavar='<port_name>', help="Display SFP presence for port <port_name> only")
def presence(port):
    """Display presence of SFP transceiver(s)"""
    logical_port_list = []
    output_table = []
    table_header = ["Port", "Presence"]

    # Create a list containing the logical port names of all ports we're interested in
    if port is None:
        logical_port_list = platform_sfputil.logical
    else:
        if platform_sfputil.is_valid_sfputil_port(port) == 0:
            click.echo("Error: invalid port '%s'\n" % port)
            print_all_valid_port_values()
            sys.exit(4)

        logical_port_list = [port]

    for logical_port_name in logical_port_list:
        ganged = False
        i = 1

        physical_port_list = logical_port_name_to_physical_port_list(logical_port_name)
        if physical_port_list is None:
            click.echo("Error: No physical ports found for logical port '%s'" % logical_port_name)
            return

        if len(physical_port_list) > 1:
            ganged = True

        for physical_port in physical_port_list:
            port_name = get_physical_port_name(logical_port_name, i, ganged)

            try:
                presence = platform_sfputil.get_presence(physical_port)
            except NotImplementedError:
                click.echo("This functionality is currently not implemented for this platform")
                sys.exit(5)

            if presence:
                output_table.append([port_name, "Present"])
            else:
                output_table.append([port_name, "Not present"])

            i += 1

    click.echo(tabulate(output_table, table_header, tablefmt="simple"))


# 'lpmode' subcommand
@show.command()
@click.option('-p', '--port', metavar='<port_name>', help="Display SFP low-power mode status for port <port_name> only")
def lpmode(port):
    """Display low-power mode status of SFP transceiver(s)"""
    logical_port_list = []
    output_table = []
    table_header = ["Port", "Low-power Mode"]

    # Create a list containing the logical port names of all ports we're interested in
    if port is None:
        logical_port_list = platform_sfputil.logical
    else:
        if platform_sfputil.is_valid_sfputil_port(port) == 0:
            click.echo("Error: invalid port '%s'\n" % port)
            print_all_valid_port_values()
            sys.exit(4)

        logical_port_list = [port]

    for logical_port_name in logical_port_list:
        ganged = False
        i = 1

        physical_port_list = logical_port_name_to_physical_port_list(logical_port_name)
        if physical_port_list is None:
            click.echo("Error: No physical ports found for logical port '%s'" % logical_port_name)
            return

        if len(physical_port_list) > 1:
            ganged = True

        for physical_port in physical_port_list:
            port_name = get_physical_port_name(logical_port_name, i, ganged)

            try:
                lpmode = platform_sfputil.get_low_power_mode(physical_port)
            except NotImplementedError:
                click.echo("This functionality is currently not implemented for this platform")
                sys.exit(5)

            if lpmode:
                output_table.append([port_name, "On"])
            else:
                output_table.append([port_name, "Off"])

            i += 1

    click.echo(tabulate(output_table, table_header, tablefmt='simple'))


# 'lpmode' subgroup
@cli.group()
def lpmode():
    """Enable or disable low-power mode for SFP transceiver"""
    pass


# Helper method for setting low-power mode
def set_lpmode(logical_port, enable):
    ganged = False
    i = 1

    if platform_sfputil.is_valid_sfputil_port(logical_port) == 0:
        click.echo("Error: invalid port '%s'\n" % logical_port)
        print_all_valid_port_values()
        sys.exit(4)

    physical_port_list = logical_port_name_to_physical_port_list(logical_port)
    if physical_port_list is None:
        click.echo("Error: No physical ports found for logical port '%s'" % logical_port)
        return

    if len(physical_port_list) > 1:
        ganged = True

    for physical_port in physical_port_list:
        click.echo("{} low-power mode for port {}... ".format(
            "Enabling" if enable else "Disabling",
            get_physical_port_name(logical_port, i, ganged)), nl=False)

        try:
            result = platform_sfputil.set_low_power_mode(physical_port, enable)
        except NotImplementedError:
            click.echo("This functionality is currently not implemented for this platform")
            sys.exit(5)

        if result:
            click.echo("OK")
        else:
            click.echo("Failed")

        i += 1


# 'off' subcommand
@lpmode.command()
@click.argument('port_name', metavar='<port_name>')
def off(port_name):
    """Disable low-power mode for SFP transceiver"""
    set_lpmode(port_name, False)


# 'on' subcommand
@lpmode.command()
@click.argument('port_name', metavar='<port_name>')
def on(port_name):
    """Enable low-power mode for SFP transceiver"""
    set_lpmode(port_name, True)


# 'reset' subcommand
@cli.command()
@click.argument('port_name', metavar='<port_name>')
def reset(port_name):
    """Reset SFP transceiver"""
    ganged = False
    i = 1

    if platform_sfputil.is_valid_sfputil_port(port_name) == 0:
        click.echo("Error: invalid port '%s'\n" % port_name)
        print_all_valid_port_values()
        sys.exit(4)

    physical_port_list = logical_port_name_to_physical_port_list(port_name)
    if physical_port_list is None:
        click.echo("Error: No physical ports found for logical port '%s'" % port_name)
        return

    if len(physical_port_list) > 1:
        ganged = True

    for physical_port in physical_port_list:
        click.echo("Resetting port %s... " % get_physical_port_name(port_name, i, ganged), nl=False)

        try:
            result = platform_sfputil.reset(physical_port)
        except NotImplementedError:
            click.echo("This functionality is currently not implemented for this platform")
            sys.exit(5)

        if result:
            click.echo("OK")
        else:
            click.echo("Failed")

        i += 1


# 'version' subcommand
@cli.command()
def version():
    """Display version info"""
    click.echo("sfputil version {0}".format(VERSION))


if __name__ == '__main__':
    cli()
