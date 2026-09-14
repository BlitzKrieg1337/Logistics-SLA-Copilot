import requests

from langchain_core.tools import tool

@tool
def calc_penalty_fx(base: str, amount: float) -> str:
    """
    Fetches the live exchange rate to convert a foreign currency into Indian Rupees (INR).
    
    Args:
        base: The 3-letter currency code you are converting FROM (e.g., "EUR", "USD").
        amount: The calculated penalty amount as a float (e.g., 1500.0).
        
    Rules:
        - ONLY use this tool if the penalty is calculated in a foreign currency.
        - DO NOT use this tool if the contract penalty is already stated in INR.
        - The conversion rate multiplier as a string, or an error message.
    """

    if base.upper() == "INR":
        return f"Final Amount: ₹{amount:,.2f} INR (No conversion needed)."

    try:
        url = f"https://api.frankfurter.dev/v2/rate/{base.upper()}/INR"

        response = requests.get(url, timeout = 10)
        response.raise_for_status()

        data = response.json()

        return f"Live FX Rate: 1 {base.upper()} = ₹{data['rate']} INR. Final converted amount -> ₹ {round(amount*data['rate'], 2)}"

    except Exception as e:
        return f"Exception -> {e}"


# if __name__ == "__main__":
#     #Test
#     print(calc_penalty_fx("GBP", 100))