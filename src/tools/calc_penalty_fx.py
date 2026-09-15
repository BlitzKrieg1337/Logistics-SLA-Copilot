import requests

from langchain_core.tools import tool

# @tool
def calc_penalty_fx(base: str, daily_rate: float, grace_period: int, delay_days: int) -> str:
    """
    Calculates the penalty (days past grace period × daily rate) and converts
    it to INR if the contract currency is not already INR.

    Args:
        base: 3-letter currency code the daily_rate is denominated in (e.g. "EUR", "USD", "INR").
        daily_rate: The per-day penalty rate as stated in the vendor contract.
        grace_period: Grace period in days per the MSA before penalties apply.
        delay_days: Total number of days the order is delayed.
    """
    billable_days = max(0, delay_days - grace_period)
    total_amount = billable_days * daily_rate

    if base.upper() == "INR":
        return f"Billable delay: {billable_days} days. Final Amount: ₹{total_amount:,.2f} INR (no conversion needed)."

    try:
        response = requests.get(f"https://api.frankfurter.dev/v2/rate/{base.upper()}/INR", timeout=10)
        response.raise_for_status()
        rate = response.json()["rate"]
        return f"Billable delay: {billable_days} days. Live FX Rate: 1 {base.upper()} = ₹{rate} INR. Final converted amount -> ₹{round(total_amount * rate, 2)}"
    except Exception as e:
        return f"Exception -> {e}"


if __name__ == "__main__":
    #Test
    print(calc_penalty_fx("GBP", 100, 0, 3))