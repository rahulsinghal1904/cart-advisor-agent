# 🍎 CartAdvisor


Online shopping often leaves customers uncertain — Is this the best deal? Should I wait? Could it be cheaper elsewhere?
**CartAdvisor Agent**  solves this by acting as a sentient shopping companion that analyzes product features, monitors competitor prices across Amazon, Walmart, and Best Buy, and checks historical trends. It proactively advises whether to buy now or wait, helping users uncover better deals and save money. Designed for real-time conversations, it thinks beyond static facts — delivering smart, human-like shopping guidance instantly!

**CartAdvisor Agent** is an intelligent, sentient shopping assistant built for the [Sentient Chat Hackathon](https://bronzed-eagle-642.notion.site/SENTIENT-CHAT-HACK-1dcab589a8518007a3c7c775d9b350f5).  

---

##  What It Does

- **Product Analysis**: Extracts and analyzes live product features and key highlights.
- **Competitor Price Comparison**: Cross-checks prices across Amazon, Walmart, Best Buy, and others.
- **Historical Price Insights**: Incorporates pricing trends to predict if better deals exist.
- **Sentient Reasoning**: Dynamically reasons through data to offer *buy now* or *wait* recommendations.
- **Real-time Chat Interface**: Seamless, human-like conversational experience to assist users instantly.

---

##  How It Solves Customer Problems

- **Reduces Uncertainty**: Provides clear, confident buying advice backed by live data.
- **Saves Money**: Identifies cheaper alternatives and highlights better timing opportunities.
- **Builds Trust**: Acts like a smart, unbiased shopping advisor.
- **Saves Time**: Replaces hours of manual research with a few seconds of intelligent chat interaction.

---

##  Why It's Sentient

Cart Advisor doesn't just fetch — it **thinks**.  
It weighs price changes, competitor offerings, product quality, and buying trends to make context-aware decisions that feel natural and human, not robotic.

---

## 🛠 Tech Stack

- **Python**, **FastAPI** (Backend)
- **Playwright** (Product Scraping)
- **BeautifulSoup** (HTML Parsing)
- **Sentient Agent Framework** (Agent Architecture)
- **Custom Reasoning Logic**
- **Inter-Chat UI** (for front-end interactions)

---

##  Setup Instructions

1. **Clone the repository**  
   ```bash
   git clone https://github.com/rahulsinghal1904/cart-advisor-agent.git
   cd cart-advisor-agent
   ```

2. **Create a Python virtual environment**  
   ```bash
   python3 -m venv venv
   source venv/bin/activate   # For Mac/Linux
   venv\Scripts\activate      # For Windows
   ```

3. **Install the required dependencies**  
   ```bash
   pip install -r requirements.txt
   ```

4. **Set environment variables**  
   Create a `.env` file in the root folder and add your API keys or credentials as needed:  
   Example `.env`:
   ```
   FIREWORKS_API_KEY=your_fireworks_api_key
   ```

5. **Run the server**  
   ```bash
   uvicorn e_commerce_agent.src.e_commerce_agent.e_commerce_agent:app --reload
   ```

6. **Interact via the chat UI**  
   Open your browser and navigate to `http://localhost:8000` or integrate it with your chat interface!

---

## 📸 Demo

| Agent in Action |
|:----------------:|

![image](https://github.com/user-attachments/assets/b91333f4-f247-4a03-bac6-37a79977d399)

![image](https://github.com/user-attachments/assets/84004099-62c6-48b8-8f0e-699b812235a6)



---

# ✨ Smart Shopping, Powered by Sentience.
