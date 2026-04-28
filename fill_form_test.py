import argparse
import random
import re
import sys
import time
from typing import List, Tuple

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

FORM_URL = (
    "https://docs.google.com/forms/d/e/"
    "1FAIpQLScpTj4fSTSHOXOE2QZLW05Z1paN5jnLrjtERnuwkKrmM0fMpw/viewform"
)

AGE_OPTIONS = ["20-25", "26-30", "30-35", "36-40", "40 above"]
EDU_OPTIONS = ["Primary", "Secondary", "Tertiary", "Postgraduate"]
YEARS_OPTIONS = ["1-5 years", "6-10 years", "11-15 years", "15 years above"]
CHURCH_OPTIONS = ["Daily", "Weekly", "Monthly"]

LIKERT_ROWS: List[str] = [
    "I maintain a consistent personal relationship with God.",
    "My faith influences my daily decisions in marriage",
    "I regularly engage in activities that strengthen my spiritual life.",
    "My connection with God helps me handle marital challenges.",
    "Spiritual growth plays an important role in my marriage.1",
    "Biblical teachings guide how I relate with my spouse.",
    "I apply scriptural principles when resolving marital conflicts.",
    "God’s word shapes my attitude toward marriage responsibilities.",
    "I rely on biblical wisdom when making decisions in my marriage.",
    "Scriptural values positively influence my marital behavior.",
    "maintain a regular personal prayer life.",
    "My spouse and I pray together consistently.",
    "Devotional activities strengthen my marriage.",
    "Prayer helps in resolving marital issues.",
    "Spiritual devotion enhances unity in my marriage.",
    "I am able to control my emotions during disagreements.",
    "My spiritual beliefs help me manage anger effectively.",
    "I respond calmly to stressful marital situations.",
    "I practice patience and understanding with my spouse.",
    "My faith helps me maintain emotional balance in marriage.",
    "I uphold Christian values such as love and respect in my marriage.",
    "Faithfulness is a guiding principle in my relationship.",
    "I strive to demonstrate forgiveness toward my spouse.",
    "My actions reflect Christ-like character in my marriage.",
    "I am committed to maintaining a God-centered marriage.",
    "I feel satisfied with my marriage overall.",
    "There is mutual understanding between my spouse and me.",
    "Communication in my marriage is effective",
    "I feel emotionally connected to my spouse.",
    "My marriage brings me a sense of fulfillment and happiness.",
]

FIRST_NAMES = [
    "Chidi",
    "Adaeze",
    "Emeka",
    "Ngozi",
    "Oluwaseun",
    "Funmi",
    "Yusuf",
    "Amina",
    "Ibrahim",
    "Kemi",
    "Tunde",
    "Chioma",
    "Obinna",
    "Halima",
    "Bukola",
    "Ifeanyi",
    "Zainab",
    "Damilola",
    "Sade",
    "Gbenga",
]

LAST_NAMES = [
    "Okafor",
    "Adeyemi",
    "Nwosu",
    "Eze",
    "Okonkwo",
    "Bello",
    "Mohammed",
    "Ajayi",
    "Ogunleye",
    "Ibrahim",
    "Adebayo",
    "Chukwu",
    "Danjuma",
    "Okafor",
    "Ezeudu",
    "Balogun",
    "Yusuf",
    "Onyeka",
    "Osagie",
    "Fashola",
]

EMAIL_DOMAINS = [
    "gmail.com",
    "yahoo.com",
    "yahoo.com.ng",
    "outlook.com",
    "hotmail.com",
]


def slug(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "", s)
    return s or "user"


def synthetic_identity() -> Tuple[str, str]:
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    email = (
        f"{slug(first)}.{slug(last)}.{random.randint(100, 9999)}"
        f"@{random.choice(EMAIL_DOMAINS)}"
    )
    return f"{first} {last}", email


def build_driver(headless: bool) -> webdriver.Chrome:
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1280,2000")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    return webdriver.Chrome(service=Service(), options=opts)


def click_radio_by_aria_label(driver: webdriver.Chrome, label: str) -> None:
    els = driver.find_elements(By.XPATH, "//div[@role='radio']")
    for el in els:
        if el.get_attribute("aria-label") != label:
            continue
        dv = el.get_attribute("data-value")
        if not dv:
            continue
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
        time.sleep(0.05)
        driver.execute_script("arguments[0].click();", el)
        return
    raise RuntimeError(f"radio not found: {label!r}")


def click_submit(driver: webdriver.Chrome) -> None:
    btn = WebDriverWait(driver, 25).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, 'div[role="button"][aria-label="Submit"]'))
    )
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
    driver.execute_script("arguments[0].click();", btn)


def wait_success_after_submit(driver: webdriver.Chrome, timeout: float) -> None:
    def _success(d: webdriver.Chrome) -> bool:
        try:
            if "formResponse" in d.current_url:
                return True
            body = d.find_element(By.TAG_NAME, "body").text or ""
            return "response has been recorded" in body.lower()
        except Exception:
            return False

    WebDriverWait(driver, timeout).until(_success)


def wait_form_ready(driver: webdriver.Chrome) -> None:
    WebDriverWait(driver, 40).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="radiogroup"]'))
    )


def go_to_next_blank_form(driver: webdriver.Chrome, form_url: str, link_wait: float) -> None:
    try:
        el = WebDriverWait(driver, link_wait).until(
            EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "Submit another response"))
        )
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
        el.click()
    except TimeoutException:
        print("Submit-another link missing; reloading form URL.", flush=True)
        driver.get(form_url)
    wait_form_ready(driver)


def fill_one_response(driver: webdriver.Chrome) -> None:
    WebDriverWait(driver, 25).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="radiogroup"]'))
    )
    click_radio_by_aria_label(driver, random.choice(AGE_OPTIONS))
    click_radio_by_aria_label(driver, random.choice(EDU_OPTIONS))
    click_radio_by_aria_label(driver, random.choice(YEARS_OPTIONS))
    click_radio_by_aria_label(driver, random.choice(CHURCH_OPTIONS))
    for row in LIKERT_ROWS:
        score = random.randint(1, 5)
        label = f"{score}, response for {row}"
        click_radio_by_aria_label(driver, label)
    click_submit(driver)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--count", type=int, default=300)
    p.add_argument("--headless", action="store_true")
    p.add_argument("--pause-min", type=float, default=1.0)
    p.add_argument("--pause-max", type=float, default=3.0)
    p.add_argument("--post-wait", type=float, default=90.0)
    p.add_argument("--link-wait", type=float, default=45.0)
    args = p.parse_args()
    if args.count < 1:
        print("count must be >= 1", file=sys.stderr)
        sys.exit(1)
    if args.pause_min > args.pause_max:
        print("pause-min must be <= pause-max", file=sys.stderr)
        sys.exit(1)

    driver = build_driver(args.headless)
    try:
        driver.get(FORM_URL)
        for i in range(args.count):
            name, email = synthetic_identity()
            print(f"[{i + 1}/{args.count}] {name} | {email}", flush=True)
            fill_one_response(driver)
            try:
                wait_success_after_submit(driver, args.post_wait)
            except TimeoutException:
                print(
                    "Success page not detected after submit; reloading form URL.",
                    flush=True,
                )
                driver.get(FORM_URL)
                wait_form_ready(driver)
                if i + 1 < args.count:
                    time.sleep(random.uniform(args.pause_min, args.pause_max))
                continue
            if i + 1 < args.count:
                go_to_next_blank_form(driver, FORM_URL, args.link_wait)
                time.sleep(random.uniform(args.pause_min, args.pause_max))
    finally:
        driver.quit()


if __name__ == "__main__":
    main()

