from pysnmp.hlapi import (
    getCmd,
    SnmpEngine,
    CommunityData,
    UdpTransportTarget,
    ContextData,
    ObjectType,
    ObjectIdentity,
    UdpTransportTarget,
)
import time
import psutil

import pandas as pd

target = "10.40.1.2"
community = "public"
networkData = {
    "inError": 0,
    "outError": 0,
    "inUnicast": 0,
    "inDiscard": 0,
    "outUnicast": 0,
    "outDiscard": 0,
    "inNonUnicast": 0,
    "outNonUnicast": 0,
    "inFacilityStats": [],
    "outFacilityStats": [],
}


def getSNMPObject(oid, community, ip, port=161):
    errorIndication, errorStatus, errorIndex, varBinds = next(
        getCmd(
            SnmpEngine(),
            CommunityData(community),
            UdpTransportTarget((ip, port)),
            ContextData(),
            ObjectType(ObjectIdentity(oid)),
        )
    )

    if errorIndication:
        print(f"SNMP Error: {errorIndication}")
        return 0
    elif errorStatus:
        print(
            f"SNMP Error: {errorStatus.prettyPrint()} at {errorIndex and varBinds[int(errorIndex) - 1][0] or '?'}"
        )
        return 0
    else:
        for varBind in varBinds:
            return int(varBind[1])
    return 0


def calculate_speed(oid, community, target, interval=1):
    first_poll = int(getSNMPObject(oid, community, target))
    time.sleep(interval)
    second_poll = int(getSNMPObject(oid, community, target))

    # Handling counter wrap
    if second_poll < first_poll:
        # Assuming a 32-bit counter, adjust this if using a different size counter
        counter_max = 2**32
        byte_diff = (counter_max - first_poll) + second_poll
    else:
        byte_diff = second_poll - first_poll

    speed_bps = (byte_diff * 8) / interval
    speed_mbps = speed_bps / 10**6
    return max(0, speed_mbps)  # Ensure negative values are not returned


def getInOutTraffic():
    in_speed = calculate_speed("1.3.6.1.2.1.2.2.1.10.1", community, target)
    out_speed = calculate_speed("1.3.6.1.2.1.2.2.1.16.1", community, target)

    yield in_speed, out_speed


def getDiscards():
    in_discards = int(getSNMPObject("1.3.6.1.2.1.2.2.1.13.1", community, target))
    out_discards = int(getSNMPObject("1.3.6.1.2.1.2.2.1.19.1", community, target))

    # print(f"Incoming Discards: {in_discards}")
    # print(f"Outgoing Discards: {out_discards}")

    yield in_discards, out_discards


def getInOutErrors():
    inError = int(getSNMPObject("1.3.6.1.2.1.2.2.1.14.1", community, target))
    outError = int(getSNMPObject("1.3.6.1.2.1.2.2.1.20.1", community, target))

    # print(f"Incoming Errors: {inError}")
    # print(f"Outgoing Errors: {outError}")

    yield inError, outError


def getInoutUnicast():
    inUnicast = int(getSNMPObject("1.3.6.1.2.1.2.2.1.11.1", community, target))
    outUnicast = int(getSNMPObject("1.3.6.1.2.1.2.2.1.17.1", community, target))

    # print(f"Incoming Unicast: {inUnicast}")
    # print(f"Outgoing Unicast: {outUnicast}")

    yield inUnicast, outUnicast


def getInOutNonUnicast():
    inNonUnicast = int(getSNMPObject("1.3.6.1.2.1.2.2.1.12.1", community, target))
    outNonUnicast = int(getSNMPObject("1.3.6.1.2.1.2.2.1.18.1", community, target))

    # print(f"Incoming Non-Unicast: {inNonUnicast}")
    # print(f"Outgoing Non-Unicast: {outNonUnicast}")

    yield inNonUnicast, outNonUnicast


# Get max, min, mean, and current traffic
def getFacilityTraffic(data):
    return {
        "average": data.mean(),
        "maximum": data.max(),
        "minimum": data.min(),
        "current": data.iloc[-1],
    }


def list_network_interfaces():
    interfaces = psutil.net_if_addrs()
    for interface_name, interface_addresses in interfaces.items():
        print(f"Interface: {interface_name}")
        for address in interface_addresses:
            if str(address.family) == "AddressFamily.AF_INET":
                print(f"  IP Address: {address.address}")
                print(f"  Netmask: {address.netmask}")
                print(f"  Broadcast IP: {address.broadcast}")
            elif str(address.family) == "AddressFamily.AF_PACKET":
                print(f"  MAC Address: {address.address}")
                print(f"  Netmask: {address.netmask}")
                print(f"  Broadcast MAC: {address.broadcast}")


def main():
    global networkData

    inOutBytes = pd.DataFrame(columns=["In", "Out"])
    inOutErrors = pd.DataFrame(columns=["In", "Out"])
    inOutUnicast = pd.DataFrame(columns=["In", "Out"])
    inOutDiscards = pd.DataFrame(columns=["In", "Out"])
    inOutNonUnicast = pd.DataFrame(columns=["In", "Out"])

    while True:
        inBytes, outBytes = next(getInOutTraffic())
        inDiscard, outDiscard = next(getDiscards())
        inError, outError = next(getInOutErrors())
        inUnicast, outUnicast = next(getInoutUnicast())
        inNonUnicast, outNonUnicast = next(getInOutNonUnicast())

        inOutBytes.loc[len(inOutBytes)] = [inBytes, outBytes]
        inOutErrors.loc[len(inOutErrors)] = [inError, outError]
        inOutUnicast.loc[len(inOutUnicast)] = [inUnicast, outUnicast]
        inOutDiscards.loc[len(inOutDiscards)] = [inDiscard, outDiscard]
        inOutNonUnicast.loc[len(inOutNonUnicast)] = [inNonUnicast, outNonUnicast]

        inFacilityStats = getFacilityTraffic(inOutBytes["In"])
        outFacilityStats = getFacilityTraffic(inOutBytes["Out"])

        networkData["inError"] = inError
        networkData["outError"] = outError
        networkData["inUnicast"] = inUnicast
        networkData["inDiscard"] = inDiscard
        networkData["outUnicast"] = outUnicast
        networkData["outDiscard"] = outDiscard
        networkData["inNonUnicast"] = inNonUnicast
        networkData["outNonUnicast"] = outNonUnicast
        networkData["inFacilityStats"] = inFacilityStats
        networkData["outFacilityStats"] = outFacilityStats

    time.sleep(1)
    # print(f"Incoming Facility Stats: {inFacilityStats}")
    # print(f"Outgoing Facility Stats: {outFacilityStats}")
    # print(f"Total Discards: {inDiscard + outDiscard}")


if __name__ == "__main__":
    list_network_interfaces()
    main()
