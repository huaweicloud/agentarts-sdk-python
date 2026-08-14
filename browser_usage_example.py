"""
Browser SDK 用户使用示例
运行方式: python browser_usage_example.py
注意: 需要设置环境变量 HUAWEICLOUD_SDK_AK、HUAWEICLOUD_SDK_SK、HUAWEICLOUD_SDK_BROWSER_API_KEY
"""

from agentarts.sdk import Browser, browser_session

# ============================================================
# 1. 初始化客户端
# ============================================================

client = Browser(
    region="cn-southwest-2",
    data_endpoint=None,     # 可选, 自定义数据面端点
    auth_type="API_KEY",    # API_KEY 或 IAM
    verify_ssl=True,        # True / False / "path/to/ca-bundle.pem"
)

# ============================================================
# 2. 管理面: 创建 Browser 资源
# ============================================================

browser = client.create_browser(
    name="my-browser",                      # 必填: ^[a-z][a-z0-9-]{0,38}[a-z0-9]$
    auth_type="API_KEY",                    # API_KEY 或 IAM
    api_key_name="my-api-key",              # API_KEY 模式必填, ^[a-zA-Z0-9_-]{1,64}$
    description="我的浏览器实例",             # 可选, 最长 4096 字符
    execution_agency_name="my-agency",      # 可选, IAM 委托名 1-64 字符
    observability={                         # 可选
        "logs": {"enabled": True, "group_id": "lg-xxx", "stream_id": "ls-xxx"},
        "metrics": {"enabled": True, "instance_id": "inst-xxx"},
        "tracing": {"enabled": False, "service_group": "sg-xxx"},
    },
    network_config={                        # 可选
        "network_mode": "PUBLIC",           # PUBLIC 或 VPC
        "vpc_config": {
            "vpc_id": None,
            "subnet_id": None,
            "security_group_ids": [],
        },
    },
    agent_gateway_id=None,                  # 可选, UUID
    tags=[{"key": "env", "value": "prod"}], # 可选, 最多 20 个
)
browser_id = browser["id"]
print(f"[OK] 创建 Browser: {browser_id}")

# ============================================================
# 3. 管理面: 查询 Browser 列表
# ============================================================

result = client.list_browsers(
    name=None,               # 可选, 按名称过滤
    offset=0,
    limit=10,
    sort_key="created_at",   # created_at 或 updated_at
    sort_dir="desc",         # asc 或 desc
    tag_key_exists=None,      # 可选, 最多 10 个
    tag_key_matches=None,     # 可选, 必须与 tag_value_matches 配对
    tag_value_matches=None,   # 可选
    tag_match_policy="ALL",   # ALL 或 ANY, 仅标签过滤时生效
)
print(f"[OK] Browser 总数: {result['total_count']}")

# ============================================================
# 4. 管理面: 查看 / 更新 / 删除 Browser
# ============================================================

browser = client.get_browser(
    browser_id=browser_id,  # 必填, UUID
)
print(f"[OK] 查看: {browser['name']}")

browser = client.update_browser(
    browser_id=browser_id,                          # 必填, UUID
    observability={"logs": {"enabled": False}},      # 可选
    tags=None,                                       # 可选
)
print(f"[OK] 更新: {browser_id}")

client.delete_browser(
    browser_id=browser_id,  # 必填, UUID
)
print(f"[OK] 删除 Browser: {browser_id}")

# ============================================================
# 5. 管理面: Browser Profile
# ============================================================

profile = client.create_browser_profile(
    name="dev-profile",                         # 必填: ^[a-z][a-z0-9-]{0,38}[a-z0-9]$
    description="开发环境配置",                   # 可选, 最长 4096 字符
    tags=[{"key": "env", "value": "dev"}],      # 可选, 最多 20 个
)
profile_id = profile["id"]
print(f"[OK] 创建 Profile: {profile_id}")

profiles = client.list_browser_profiles(
    name=None,
    offset=0,
    limit=10,
    sort_key="created_at",
    sort_dir="desc",
    tag_key_exists=None,
    tag_key_matches=None,
    tag_value_matches=None,
    tag_match_policy="ALL",
)
print(f"[OK] Profile 总数: {profiles['total_count']}")

profile = client.get_browser_profile(
    profile_id=profile_id,  # 必填, UUID
)

client.delete_browser_profile(
    profile_id=profile_id,  # 必填, UUID
)
print(f"[OK] 删除 Profile: {profile_id}")

# ============================================================
# 6. 数据面: 启动会话
# ============================================================

session = client.start_session(
    browser_name="my-browser",              # 必填
    session_id="my-session-001",            # 必填, 客户端指定
    session_name="my-session",              # 必填, ^[a-zA-Z0-9_-]{1,128}$
    browser_id=None,                        # 可选
    view_point=None,                        # 可选, {"width": 1920, "height": 1080}
    profile_configuration=None,             # 可选
    allowed_domains=None,                   # 可选, 与 blocked_domains 互斥
    blocked_domains=None,                   # 可选
    proxy_configuration=None,               # 可选, {"proxy_url": "http://..."}
    session_timeout=900,                    # 可选, 默认 900 秒
    api_key=None,                           # 可选, API_KEY 模式时自动从环境变量取
)
print(f"[OK] 启动会话: {client.session_id}")

# ============================================================
# 7. 数据面: 浏览器操作 (全部走 invoke)
# ============================================================

# 鼠标操作
client.left_mouse_click(x=100, y=200, api_key=None)
client.right_mouse_click(x=100, y=200, api_key=None)
client.double_mouse_click(x=100, y=200, api_key=None)
client.mouse_move(x=300, y=400, api_key=None)
client.mouse_drag(
    start_x=100, start_y=100,
    end_x=200, end_y=200,
    button="left",         # left / right / middle
    api_key=None,
)

# 滚动
client.mouse_scroll(x=500, y=300, delta_x=0, delta_y=-100, api_key=None)

# 键盘
client.key_press(key="Enter", presses=1, api_key=None)
client.key_press(key="Tab", presses=3, api_key=None)
client.key_type(text="Hello, World!", api_key=None)
client.key_shortcut(keys=["Control", "c"], api_key=None)

# 导航
client.navigate(url="https://example.com", api_key=None)
client.go_back(api_key=None)
client.go_forward(api_key=None)
client.refresh(api_key=None)

# 页面信息
client.get_page_info(api_key=None)
client.screenshot(
    format="jpeg",          # png 或 jpeg
    quality=80,             # 1-100, 仅 jpeg 时生效
    full_page=False,        # 是否截取整个页面
    api_key=None,
)
client.wait(duration=2.5, api_key=None)  # 0.1 - 30 秒

# 标签页
client.list_tabs(api_key=None)
client.switch_tab(tab_id="tab-1", api_key=None)
client.close_tab(tab_id="tab-1", api_key=None)
client.new_tab(url="https://example.com", api_key=None)

print("[OK] 所有操作执行完毕")

# ============================================================
# 8. 数据面: 查询 / 保存会话
# ============================================================

session_info = client.get_session(
    api_key=None,
)
print(f"[OK] 会话状态: {session_info}")

client.save_profile(
    profile_id="my-profile-id",
    api_key=None,
)
print("[OK] 已保存 Profile")

# ============================================================
# 9. 人工接管控制
# ============================================================

client.take_control(
    client_token=None,   # 可选, 幂等 token
    api_key=None,
)
# ... 人工操作浏览器 ...
client.release_control(
    client_token=None,
    api_key=None,
)

# 或者直接使用底层方法
client.update_stream(
    stream_status="enabled",    # disabled 或 enabled
    client_token=None,
    api_key=None,
)

# ============================================================
# 10. WebSocket 连接
# ============================================================

ws_url, ws_headers = client.generate_automation_url(
    api_key=None,
)
print(f"[OK] Automation WS: {ws_url}")

ws_url, ws_headers = client.generate_live_view_url(
    api_key=None,
)
print(f"[OK] LiveView WS: {ws_url}")

# ============================================================
# 11. 停止会话
# ============================================================

client.stop_session(
    api_key=None,
)
print("[OK] 会话已停止")

# ============================================================
# 12. 使用上下文管理器 (推荐)
# ============================================================

with browser_session(
    region="cn-southwest-2",
    browser_name="my-browser",
    session_id="session-002",
    session_name="my-session",
    auth_type="API_KEY",
    api_key=None,
    verify_ssl=True,
) as b:
    b.navigate("https://example.com")
    b.screenshot()
    # 离开 with 块自动调 stop_session()
print("[OK] 上下文管理器测试完成")
