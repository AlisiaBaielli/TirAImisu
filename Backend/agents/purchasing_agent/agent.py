from browser_use import Agent, Browser, ChatBrowserUse
import asyncio
import dotenv

dotenv.load_dotenv()
# ─────────────────────────────────────────────────────────────
USER = {
    "first_name": "Jan",
    "last_name": "Jansen",
    "email": "jan.jansen@example.com",
    "phone": "0612345678",
    "street": "Keizersgracht 1",
    "postal_code": "1015CS",
    "city": "Amsterdam",
    "country": "Netherlands",
}

PRODUCT = {
    "name": "Paracetamol 500 mg",
    "quantity": 2,  # number of boxes / packs to buy
}

STORE = {
    "base_url": "https://www.drogist.nl/",
    "locale_hint": "Site is in Dutch; you can use the search field.",
}


# ─────────────────────────────────────────────────────────────
# Task prompt for the agent
# ─────────────────────────────────────────────────────────────
def build_task(user, product, store) -> str:
    return f"""
You are a careful shopping assistant automating a browser.

GOAL
- On {store['base_url']} search for: "{product['name']}".
- Select an in-stock product that clearly matches the requested name and strength (no substitutes).
- Set quantity to {product['quantity']} and add to cart.
- Proceed to checkout and fill shipping details using the info below.
- STOP BEFORE PAYMENT and summarize the checkout state (cart items, quantity, subtotal, shipping method).
- Provide screenshots or captured evidence if your environment allows. Return a step-by-step action log.

USER DETAILS (use exactly as written; do not invent data)
- First name: {user['first_name']}
- Last name: {user['last_name']}
- Email: {user['email']}
- Phone: {user['phone']}
- Street: {user['street']}
- Postal code: {user['postal_code']}
- City: {user['city']}
- Country: {user['country']}

CONSTRAINTS
- Stay on the domain drogist.nl.
- If a cookie/consent banner appears, accept minimal cookies to proceed.
- Language: the site is Dutch; use the search bar (look for 'Zoeken').
- If the exact product is not found, DO NOT buy alternatives; stop and report.
- If the site requires account login, choose guest checkout if possible.
- Payment step: DO NOT place or authorize payment. Stop at the payment method screen and summarize.
- Robustness: if the DOM changes or an element is not found, retry via the site's search input.
- Always report: final URL, items in cart, unit price, quantity, subtotal, shipping method (if any).

OUTPUT
- A concise summary with:
  - success/failure,
  - product title you picked,
  - quantity in cart,
  - price(s) found,
  - subtotal,
  - shipping option chosen,
  - current page URL,
  - any blockers encountered.
"""


# ─────────────────────────────────────────────────────────────
# Runner
# ─────────────────────────────────────────────────────────────
async def run_demo():
    if Agent is None:
        print(
            "browser-use is not installed yet. This is the prompt-only demo scaffold."
        )
        print(
            "Once installed, this script will instruct the agent to navigate drogist.nl and stop before payment."
        )
        return

    # You can pass args to Browser() if you need headless=False for debugging.
    browser = Browser(
        # headless=False,           # uncomment for visible browser during dev
        # use_cloud=True,           # if you have Browser Use Cloud
        # start_url=STORE["base_url"]
    )

    llm = ChatBrowserUse()

    agent = Agent(
        task=build_task(USER, PRODUCT, STORE),
        llm=llm,
        browser=browser,
        # Optional: guardrails if the library supports them in your version
        # allowed_domains=["www.drogist.nl", "drogist.nl"],
        # max_actions=40,
        # timeout=300,
    )

    history = await agent.run()
    return history


if __name__ == "__main__":
    asyncio.run(run_demo())
