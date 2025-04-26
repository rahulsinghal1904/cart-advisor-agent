# test.py

from utils import fetch_amazon_details

url = "https://www.amazon.com/MoKo-Generation-Stand-Translucent-Support/dp/B0B8STRJYJ/?_encoding=UTF8&pd_rd_w=tMDEP&content-id=amzn1.sym.f2128ffe-3407-4a64-95b5-696504f68ca1&pf_rd_p=f2128ffe-3407-4a64-95b5-696504f68ca1&pf_rd_r=S806248SJ689DFM2P43T&pd_rd_wg=7ihvB&pd_rd_r=d58cadca-d086-4b0c-a9e8-18370f935b72&ref_=pd_hp_d_btf_crs_zg_bs_541966"  # Example Amazon product URL

details = fetch_amazon_details(url)
print(details)
