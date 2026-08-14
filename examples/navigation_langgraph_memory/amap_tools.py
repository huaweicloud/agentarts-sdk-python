"""
Navigation Agent Demo - AMap (Gaode Maps) Tools

Python port of the original amap-lbs-skill/index.js. Exposes four
LangChain tools: geocode_address, search_poi, plan_route,
generate_map_link.

When AMAP_KEY is not set, tools return mock data so the agent graph
can be exercised end-to-end without a real AMap key.
"""

import json
import urllib.parse

import requests
from langchain_core.tools import tool

import cli_flags  # noqa: F401
import config  # noqa: F401  (sets env vars as side effect)
from config import AMAP_BASE, AMAP_KEY

_mock_warned = False


def _warn_mock():
    """Print mock data warning once in debug mode."""
    global _mock_warned
    if not _mock_warned and cli_flags.DEBUG:
        print("[MOCK] AMAP_KEY not set - using simulated data.")
        print("[MOCK] Set AMAP_KEY env var to enable real AMap API calls.")
    _mock_warned = True


def _safe_get(url, params, timeout=10):
    """Wrapper around requests.get with error handling.

    Returns (data_dict, None) on success, (None, error_str) on failure.
    """
    try:
        resp = requests.get(url, params=params, timeout=timeout)
        return resp.json(), None
    except requests.exceptions.Timeout:
        return None, f"Request timed out after {timeout}s"
    except requests.exceptions.ConnectionError as e:
        return None, f"Connection error: {e}"
    except requests.exceptions.RequestException as e:
        return None, f"Request failed: {e}"
    except (ValueError, KeyError) as e:
        return None, f"Response parse error: {e}"


# ---------------------------------------------------------------------------
# Mock data
# ---------------------------------------------------------------------------

_MOCK_POIS = {
    "加油站": [
        {"name": "中石化朝阳加油站", "address": "北京市朝阳区朝阳路88号",
         "location": "116.481181,39.990021", "tel": "010-12345678",
         "type": "加油站", "distance": ""},
        {"name": "中石油建国路加油站", "address": "北京市朝阳区建国路100号",
         "location": "116.461810,39.921000", "tel": "010-87654321",
         "type": "加油站", "distance": ""},
        {"name": "壳牌三环加油站", "address": "北京市丰台区南三环西路6号",
         "location": "116.378432,39.865000", "tel": "010-11112222",
         "type": "加油站", "distance": ""},
    ],
    "餐厅": [
        {"name": "全聚德烤鸭店(前门店)", "address": "北京市东城区前门大街30号",
         "location": "116.397428,39.898556", "tel": "010-65112233",
         "type": "中餐厅", "distance": ""},
        {"name": "海底捞火锅(朝阳大悦城店)", "address": "北京市朝阳区朝阳北路101号",
         "location": "116.510181,39.930230", "tel": "010-85556666",
         "type": "火锅店", "distance": ""},
    ],
    "停车场": [
        {"name": "国贸地下停车场", "address": "北京市朝阳区建国门外大街1号",
         "location": "116.461810,39.908000", "tel": "",
         "type": "停车场", "distance": ""},
        {"name": "三里屯SOHO停车场", "address": "北京市朝阳区三里屯路19号",
         "location": "116.454350,39.935580", "tel": "",
         "type": "停车场", "distance": ""},
    ],
}

_MOCK_DEFAULT = [
    {"name": "示例地点A", "address": "示例地址1", "location": "116.480000,39.990000",
     "tel": "", "type": "", "distance": ""},
    {"name": "示例地点B", "address": "示例地址2", "location": "116.460000,39.920000",
     "tel": "", "type": "", "distance": ""},
]

_MOCK_GEOCODE = {
    "formatted_address": "北京市海淀区中关村",
    "location": "116.310003,39.991957",
}


def _mock_pois(keywords, city):
    """Return mock POI data for given keywords, optionally prefixed with city."""
    _warn_mock()
    pois = _MOCK_POIS.get(keywords, _MOCK_DEFAULT)
    if city:
        pois = [dict(p, address=f"{city}{p['address']}") for p in pois]
    return json.dumps(pois, ensure_ascii=False)


def _mock_route(origin, destination, mode):
    """Return mock route data with navigation link for given origin/destination/mode."""
    _warn_mock()
    mode_label = {"driving": "驾车", "walking": "步行", "riding": "骑行",
                  "transit": "公交"}.get(mode, mode)
    # Map internal mode names to AMap URI API mode values
    uri_mode = {"driving": "car", "walking": "walk",
                "riding": "ride", "transit": "bus"}.get(mode, "car")
    nav_link = (
        f"https://uri.amap.com/navigation?from={origin},start"
        f"&to={destination},end&mode={uri_mode}&policy=1&src=mypage&callnative=0"
    )
    return json.dumps({
        "mode": mode_label,
        "distance_m": "12500" if mode == "driving" else "3200",
        "duration_s": "1680" if mode == "driving" else "2700",
        "tolls": "0" if mode == "driving" else "",
        "traffic_lights": "8" if mode == "driving" else "",
        "cost": "",
        "nav_link": nav_link,
        "note": "Mock route - set AMAP_KEY for real data.",
    }, ensure_ascii=False)


def _mock_geocode(address):
    """Return mock geocode result for given address."""
    _warn_mock()
    result = dict(_MOCK_GEOCODE)
    result["formatted_address"] = f"{address}（模拟地址）"
    return json.dumps(result, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@tool
def geocode_address(address: str, city: str = "") -> str:
    """Convert a place name or address to coordinates.

    Use this when the user gives a place name (e.g. "中关村", "南京站")
    instead of coordinates, before calling plan_route or search_poi
    with location.

    Args:
        address: Place name or address, e.g. "中关村", "南京南站"
        city: City to narrow search, e.g. "北京". Optional.

    Returns:
        JSON with formatted_address and location ("lng,lat"),
        or error message.
    """
    if not AMAP_KEY:
        return _mock_geocode(address)

    params = {"key": AMAP_KEY, "address": address}
    if city:
        params["city"] = city

    data, err = _safe_get(f"{AMAP_BASE}/v3/geocode/geo", params)
    if err:
        return f"Geocode failed: {err}"
    if data.get("status") != "1":
        return f"Geocode failed: {data.get('info', 'unknown error')}"

    geocodes = data.get("geocodes", [])
    if not geocodes:
        return f"No coordinates found for '{address}'"

    g = geocodes[0]
    return json.dumps({
        "formatted_address": g.get("formatted_address", ""),
        "location": g.get("location", ""),
    }, ensure_ascii=False)


@tool
def search_poi(keywords: str, city: str = "", location: str = "",
               radius: int = 3000, types: str = "") -> str:
    """Search for points of interest (POI). Supports keyword search and
    nearby search around a center point.

    Args:
        keywords: Search terms, e.g. "加油站" (gas station), "餐厅" (restaurant)
        city: City name to narrow the search, e.g. "北京". Optional.
        location: Center coordinates "lng,lat" for nearby search. When
            provided, searches within radius of this point. Optional.
        radius: Search radius in meters when location is given. Default 3000.
        types: POI type code filter, e.g. "010000" for gas station. Optional.

    Returns:
        JSON list of POIs, each with name, address, location, tel, type,
        and distance (from center, if applicable).
    """
    if not AMAP_KEY:
        return _mock_pois(keywords, city)

    params = {
        "key": AMAP_KEY,
        "keywords": keywords,
        "region": city,
        "city_limit": "true" if city else "false",
        "page_size": 5,
        "page": 1,
    }
    if location:
        params["location"] = location
        params["radius"] = radius
        params["sortrule"] = "distance"
    if types:
        params["types"] = types

    data, err = _safe_get(f"{AMAP_BASE}/v5/place/text", params)
    if err:
        return f"Search failed: {err}"
    if data.get("status") != "1":
        return f"Search failed: {data.get('info', 'unknown error')}"

    pois = data.get("pois", [])[:5]
    if not pois:
        return f"No results found for '{keywords}' in '{city or 'all'}'"

    results = [
        {
            "name": p.get("name", ""),
            "address": p.get("address", ""),
            "location": p.get("location", ""),
            "tel": p.get("tel", ""),
            "type": p.get("type", ""),
            "distance": p.get("distance", ""),
        }
        for p in pois
    ]
    return json.dumps(results, ensure_ascii=False)


@tool
def plan_route(origin: str, destination: str, mode: str = "driving",
               waypoints: str = "", city: str = "") -> str:
    """Plan a route from origin to destination.

    Args:
        origin: Start coordinates as "longitude,latitude"
            e.g. "116.481181,39.990021"
        destination: End coordinates as "longitude,latitude"
        mode: Travel mode - one of: driving, walking, riding, transit.
            Default: driving.
        waypoints: Intermediate stops for driving only, format
            "lng,lat;lng,lat" (up to 16 stops, semicolon-separated). Optional.
        city: City name, required for transit mode. Optional for others.

    Returns:
        JSON with distance, duration, navigation link, and mode-specific
        details (tolls/traffic_lights for driving, cost for transit).
    """
    if not AMAP_KEY:
        return _mock_route(origin, destination, mode)

    if mode == "walking":
        url = f"{AMAP_BASE}/v3/direction/walking"
        params = {"key": AMAP_KEY, "origin": origin, "destination": destination}
    elif mode == "driving":
        url = f"{AMAP_BASE}/v3/direction/driving"
        params = {
            "key": AMAP_KEY, "origin": origin, "destination": destination,
            "strategy": 10, "extensions": "base",
        }
        if waypoints:
            params["waypoints"] = waypoints
    elif mode == "riding":
        url = f"{AMAP_BASE}/v4/direction/bicycling"
        params = {"key": AMAP_KEY, "origin": origin, "destination": destination}
    elif mode == "transit":
        url = f"{AMAP_BASE}/v3/direction/transit/integrated"
        if not city:
            return "Transit mode requires 'city' parameter."
        params = {
            "key": AMAP_KEY, "origin": origin, "destination": destination,
            "city": city, "strategy": 0,
        }
    else:
        return f"Invalid mode '{mode}'. Use: driving, walking, riding, transit"

    data, err = _safe_get(url, params, timeout=15)
    if err:
        return f"Route planning failed: {err}"

    # riding uses errcode, others use status
    ok = data.get("status") == "1" or data.get("errcode") == 0
    if not ok:
        msg = data.get("info") or data.get("errmsg", "unknown")
        return f"Route planning failed: {msg}"

    # transit uses route.transits, others use route.paths
    route_root = data.get("route", {})
    if mode == "transit":
        transits = route_root.get("transits", [])
        route = transits[0] if transits else {}
        distance = route.get("distance", "N/A")
        duration = route.get("duration", "N/A")
        cost_info = route.get("cost", {})
        if isinstance(cost_info, dict):
            duration = cost_info.get("duration", duration)
            cost = cost_info.get("transit_fee", "")
        else:
            cost = str(cost_info) if cost_info else ""
        tolls = ""
        traffic_lights = ""
    else:
        route = route_root.get("paths", [{}])[0]
        distance = route.get("distance", "N/A")
        duration = route.get("duration", "N/A")
        tolls = ""
        traffic_lights = ""
        cost = ""
        if mode == "driving":
            tolls = route.get("tolls", "")
            traffic_lights = route.get("traffic_lights", "")

    # Map internal mode names to AMap URI API mode values
    mode_map = {
        "driving": "car",
        "walking": "walk",
        "riding": "ride",
        "transit": "bus",
    }
    uri_mode = mode_map.get(mode, "car")
    nav_link = (
        f"https://uri.amap.com/navigation?from={origin},start"
        f"&to={destination},end&mode={uri_mode}&policy=1&src=mypage&callnative=0"
    )
    if waypoints and mode == "driving":
        nav_link += f"&via={waypoints},midway"
    return json.dumps({
        "mode": mode,
        "distance_m": distance,
        "duration_s": duration,
        "tolls": tolls,
        "traffic_lights": traffic_lights,
        "cost": cost,
        "nav_link": nav_link,
    }, ensure_ascii=False)


@tool
def generate_map_link(pois: str) -> str:
    """Generate a map visualization link showing one or more locations.

    Args:
        pois: JSON string of a list, each item like
            {"name": "...", "lnglat": [longitude, latitude]}

    Returns:
        A URL that opens an AMap visualization page with markers.
    """
    try:
        poi_list = json.loads(pois) if isinstance(pois, str) else pois
    except (json.JSONDecodeError, TypeError):
        return "Invalid pois format. Provide JSON list of {name, lnglat}."

    map_data = []
    for p in poi_list:
        lnglat = p.get("lnglat") or p.get("location")
        if isinstance(lnglat, str):
            parts = lnglat.split(",")
            lnglat = [float(parts[0]), float(parts[1])]
        map_data.append({
            "type": "poi",
            "lnglat": lnglat,
            "text": p.get("name", ""),
            "remark": p.get("address", ""),
        })

    data_str = urllib.parse.quote(json.dumps(map_data, ensure_ascii=False))
    return f"https://a.amap.com/jsapi_demo_show/static/openclaw/travel_plan.html?data={data_str}"
