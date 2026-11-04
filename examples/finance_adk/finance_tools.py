"""
Finance Agent Demo - Tool Functions

5 tools:
  1. record_expense()    — Record a new expense (local JSON)
  2. query_expenses()    — Query expense records (local JSON)
  3. analyze_spending() — Data analysis via Code Interpreter
  4. generate_chart()    — Chart generation via Code Interpreter
  5. recall_memory()     — Deep memory search via Memory Service
     (defined in memory_tools.py, imported here)
"""

import json
import os
from contextlib import contextmanager

from google.adk.tools import FunctionTool

import config
from agentarts.sdk.tools.code_interpreter import CodeInterpreter
from expense_store import add_expense, query, get_period_data
from memory_tools import recall_memory_impl


# ---------------------------------------------------------------------------
# Helper: Code Interpreter response parsing + session management
# ---------------------------------------------------------------------------
def _extract_code_output(result: dict) -> tuple[str, bool]:
    """从 execute_code 返回值中提取文本和错误标志。

    API 返回结构:
      正常: {"result": {"content": [{"type":"text","text":"..."}], "is_error": false}}
      异常: {"result": {"content": [{"type":"text","text":"ValueError: ..."}], "is_error": true}}

    Returns:
        (combined_text, is_error)
    """
    result_inner = result.get("result", {})
    content_items = result_inner.get("content", [])
    is_error = result_inner.get("is_error", False)
    texts = [
        item.get("text", "")
        for item in content_items
        if item.get("type") == "text"
    ]
    return "\n".join(texts).strip(), is_error


@contextmanager
def _code_session():
    """Code Interpreter 会话上下文管理器。

    直接使用 SDK 默认配置。SDK 的 HTTP 请求超时为 30s（RequestConfig 默认值）。

    注意：若你的环境中 start_session 冷启动超过 30s 导致超时失败
    （SDK 的 CodeInterpreter/DataToolsHttpClient 未暴露 timeout 参数），
    可解除下面注释，将 HTTP 超时提升到 180s：
    """
    client = CodeInterpreter(
        region=config.CODE_INTERPRETER_REGION,
        verify_ssl=config.VERIFY_SSL,
    )
    # 恢复 180s 超时的备选方案（默认使用 SDK 的 30s）：
    #   from agentarts.sdk.service.http_client import RequestConfig
    #   client.data_plane_client._config = RequestConfig(
    #       base_url=client.data_plane_client._config.base_url,
    #       timeout=180.0,
    #       headers=client.data_plane_client._config.headers,
    #       verify_ssl=client.data_plane_client._config.verify_ssl,
    #   )
    client.start_session(
        code_interpreter_name=config.CODE_INTERPRETER_NAME,
        session_name="finance-demo",
        api_key=config.CODE_INTERPRETER_API_KEY,
    )
    try:
        yield client
    finally:
        client.stop_session(api_key=config.CODE_INTERPRETER_API_KEY)


# ---------------------------------------------------------------------------
# Tool 1: record_expense
# ---------------------------------------------------------------------------
async def record_expense(
    amount: float,
    category: str,
    note: str = "",
    date: str = "",
) -> str:
    """Record a new expense.

    Args:
        amount: The expense amount in CNY (yuan).
        category: Expense category. One of: dining, transport, shopping,
            entertainment, housing, healthcare, education, other.
        note: Optional note describing the expense.
        date: Optional date in YYYY-MM-DD format. Defaults to today.

    Returns:
        Confirmation message with the recorded expense details.
    """
    record = add_expense(
        amount=amount,
        category=category,
        note=note,
        date=date or None,
    )
    return (
        f"Recorded: {record['amount']} CNY on {record['category']} "
        f"({record['date']}). Note: {record['note'] or 'N/A'}. ID: {record['id']}"
    )


# ---------------------------------------------------------------------------
# Tool 2: query_expenses
# ---------------------------------------------------------------------------
async def query_expenses(
    start_date: str = "",
    end_date: str = "",
    category: str = "",
) -> str:
    """Query expense records by date range and/or category.

    Args:
        start_date: Start date (YYYY-MM-DD). Empty for no lower bound.
        end_date: End date (YYYY-MM-DD). Empty for no upper bound.
        category: Filter by category. Empty for all categories.

    Returns:
        JSON string of matching expense records.
    """
    results = query(
        start_date=start_date or None,
        end_date=end_date or None,
        category=category or None,
    )
    if not results:
        return "No expenses found matching the criteria."
    total = sum(r["amount"] for r in results)
    summary = f"Found {len(results)} records, total: {total:.2f} CNY.\n"
    return summary + json.dumps(results, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Tool 3: analyze_spending (Code Interpreter)
# ---------------------------------------------------------------------------
VALID_ANALYSIS_TYPES = {"summary", "trend", "compare"}

_ANALYSIS_SCRIPT = """
import json
import pandas as pd

with open("/home/user/expenses.json", "r", encoding="utf-8") as f:
    data = json.load(f)

df = pd.DataFrame(data)
df["date"] = pd.to_datetime(df["date"])
df["amount"] = df["amount"].astype(float)

analysis_type = "{analysis_type}"

if analysis_type == "summary":
    summary = df.groupby("category")["amount"].agg(["sum", "count"])
    summary["pct"] = (summary["sum"] / summary["sum"].sum() * 100).round(1)
    print(summary.to_string())
    print(f"\\nTotal: {df['amount'].sum():.2f} CNY")

elif analysis_type == "trend":
    daily = df.groupby(df["date"].dt.date)["amount"].sum()
    print("Daily spending trend:")
    print(daily.to_string())
    print(f"\\nAvg/day: {daily.mean():.2f} CNY")
    print(f"Max day: {daily.max():.2f} CNY ({daily.idxmax()})")

elif analysis_type == "compare":
    # Compare first half vs second half of the period
    mid = len(df) // 2
    first_half = df.iloc[:mid]["amount"].sum()
    second_half = df.iloc[mid:]["amount"].sum()
    print(f"First half:  {first_half:.2f} CNY")
    print(f"Second half: {second_half:.2f} CNY")
    diff = second_half - first_half
    pct = (diff / first_half * 100) if first_half else 0
    print(f"Change: {diff:+.2f} CNY ({pct:+.1f}%)")
"""


async def analyze_spending(
    analysis_type: str,
    period: str = "this_month",
) -> str:
    """Analyze spending data using a code interpreter sandbox.

    Runs pandas-based analysis on stored expense records.

    Args:
        analysis_type: Type of analysis to run.
            "summary" - Category breakdown with percentages
            "trend" - Daily spending trend
            "compare" - Period-over-period comparison
        period: Time period to analyze.
            "this_month" - Current month
            "last_month" - Last month
            "all" - All recorded data

    Returns:
        Text output of the analysis.
    """
    # 0. Validate parameters before starting a sandbox session
    #    (avoids wasting a 30s+ session start on invalid input)
    if analysis_type not in VALID_ANALYSIS_TYPES:
        return f"Invalid analysis_type: {analysis_type}. Valid options: {VALID_ANALYSIS_TYPES}"

    # 1. Collect expense data from local store
    data = get_period_data(period)
    if not data:
        return f"No expense data found for period: {period}"

    # 2. Run analysis in Code Interpreter sandbox
    with _code_session() as code_client:
        # Upload data
        code_client.upload_file(
            "/home/user/expenses.json",
            json.dumps(data, ensure_ascii=False),
            description="Expense records JSON",
        )

        # 安装 pandas（沙箱可能未预装）
        code_client.install_packages(["pandas"])

        # Execute analysis script
        # 使用 replace 而非 format，因为脚本中包含 f-string（如 {df['amount'].sum()}），
        # format() 会误解析 f-string 中的花括号导致 KeyError
        script = _ANALYSIS_SCRIPT.replace("{analysis_type}", analysis_type)
        result = code_client.execute_code(script)

        text, is_error = _extract_code_output(result)
        if is_error:
            return f"Analysis failed:\n{text}"
        return text if text else "Analysis produced no output."


# ---------------------------------------------------------------------------
# Tool 4: generate_chart (Code Interpreter)
# ---------------------------------------------------------------------------
VALID_CHART_TYPES = {"pie", "bar", "line"}

_CHART_SCRIPT = """
import json
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import pandas as pd

with open("/home/user/expenses.json", "r", encoding="utf-8") as f:
    data = json.load(f)

df = pd.DataFrame(data)
df["amount"] = df["amount"].astype(float)

chart_type = "{chart_type}"
output_path = "/home/user/chart.png"

if chart_type == "pie":
    summary = df.groupby("category")["amount"].sum()
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.pie(summary.values, labels=summary.index, autopct="%1.1f%%",
           startangle=90)
    ax.set_title("Spending by Category")
    plt.tight_layout()

elif chart_type == "bar":
    summary = df.groupby("category")["amount"].sum().sort_values(ascending=True)
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.barh(summary.index, summary.values, color="steelblue")
    ax.set_xlabel("Amount (CNY)")
    ax.set_title("Spending by Category")
    plt.tight_layout()

elif chart_type == "line":
    df["date"] = pd.to_datetime(df["date"])
    daily = df.groupby(df["date"].dt.date)["amount"].sum()
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(daily.index, daily.values, marker="o", color="steelblue")
    ax.set_xlabel("Date")
    ax.set_ylabel("Amount (CNY)")
    ax.set_title("Daily Spending Trend")
    plt.tight_layout()

fig.savefig(output_path, dpi=150)
print(f"Chart saved to {output_path}")
"""


async def generate_chart(
    chart_type: str,
    period: str = "this_month",
) -> str:
    """Generate a visual chart of spending data.

    Uses a code interpreter sandbox to create matplotlib charts.

    Args:
        chart_type: Type of chart to generate.
            "pie" - Category breakdown pie chart
            "bar" - Category comparison bar chart
            "line" - Daily spending trend line chart
        period: Time period to chart.
            "this_month" - Current month
            "last_month" - Last month
            "all" - All recorded data

    Returns:
        Path to the generated chart file, or an error message.
    """
    # 0. Validate parameters before starting a sandbox session
    #    (avoids wasting a 30s+ session start on invalid input)
    if chart_type not in VALID_CHART_TYPES:
        return f"Invalid chart_type: {chart_type}. Valid options: {VALID_CHART_TYPES}"

    data = get_period_data(period)
    if not data:
        return f"No expense data found for period: {period}"

    with _code_session() as code_client:
        # Upload data
        code_client.upload_file(
            "/home/user/expenses.json",
            json.dumps(data, ensure_ascii=False),
            description="Expense records JSON",
        )

        # Install matplotlib + pandas（沙箱可能未预装）
        code_client.install_packages(["matplotlib", "pandas"])

        # Generate chart
        # 使用 replace 而非 format，因为脚本中包含 f-string（如 {output_path}），
        # format() 会误解析 f-string 中的花括号导致 KeyError
        script = _CHART_SCRIPT.replace("{chart_type}", chart_type)
        result = code_client.execute_code(script)

        text, is_error = _extract_code_output(result)
        if is_error:
            return f"Chart generation failed:\n{text}"
        if "Chart saved" not in text:
            return f"Chart generation may have failed: {text}"

        # Download the chart
        chart_bytes = code_client.download_file("/home/user/chart.png")
        # Save to local file for display
        chart_path = os.path.join(
            os.path.dirname(config.EXPENSES_FILE),
            f"chart_{chart_type}_{period}.png",
        )
        with open(chart_path, "wb") as f:
            f.write(chart_bytes)

        return f"Chart generated successfully: {chart_type} chart for {period}. " \
               f"Saved to: {chart_path}"


# ---------------------------------------------------------------------------
# Tool 5: recall_memory (defined in memory_tools.py)
# ---------------------------------------------------------------------------
# See memory_tools.py for implementation


# ---------------------------------------------------------------------------
# Register all tools as FunctionTools
# ---------------------------------------------------------------------------
all_tools = [
    FunctionTool(func=record_expense),
    FunctionTool(func=query_expenses),
    FunctionTool(func=analyze_spending),
    FunctionTool(func=generate_chart),
    FunctionTool(func=recall_memory_impl),  # from memory_tools.py
]
