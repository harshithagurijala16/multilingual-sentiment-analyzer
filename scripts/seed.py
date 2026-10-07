import sys
import os
import random
from datetime import datetime, timedelta, timezone

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import engine, Base, SessionLocal
from app.models import User, Product, Review
from app.auth import hash_password
from src.nlp.pipeline import analyze_review

REVIEWS_SEEDS = [
    # Telugu
    ("ఈ మొబైల్ కెమెరా చాలా అద్భుతంగా ఉంది, బ్యాటరీ లైఫ్ రెండు రోజులు వస్తుంది.", "Telugu", "Positive"),
    ("ఈ ఉత్పత్తి నాణ్యత చాలా దారుణంగా ఉంది, వెంటనే పాడైపోయింది.", "Telugu", "Negative"),
    ("naku ee product chala nachindi, delivery kuda super fast ga vachindi", "Telugu", "Positive"),
    ("chala darunam ga undi quality, charge pettina on avvatledu waste of money", "Telugu", "Negative"),
    ("paravaledu normal ga undi, display average performance", "Telugu", "Neutral"),
    ("sound clarity superga undi bass kuda bavundi highly recommended", "Telugu", "Positive"),
    ("speaker sound chala takkuva ga undi, call quality bavoledu", "Telugu", "Negative"),
    ("ధర కొంచెం ఎక్కువే కానీ క్వాలిటీ బాగుంది.", "Telugu", "Positive"),
    ("డెలివరీ చాలా లేట్ అయింది, ప్యాకేజింగ్ చిరిగిపోయింది.", "Telugu", "Negative"),
    ("battery backup bagundi kaani heating problem undi", "Telugu", "Neutral"),
    ("super phone bro, gaming lo asalu lag ledu chala bagundi", "Telugu", "Positive"),
    ("service center vallu response ivvatledu worst experience", "Telugu", "Negative"),
    ("ఈ హెడ్‌ఫోన్స్ సౌండ్ చాలా క్లియర్‌గా ఉంది.", "Telugu", "Positive"),
    ("కాల్ మాట్లాడేటప్పుడు మైక్ సరిగ్గా పనిచేయడం లేదు.", "Telugu", "Negative"),
    ("okati rendo rojullo vachindi, product okay", "Telugu", "Neutral"),

    # Hindi
    ("यह फोन बहुत ही शानदार है, इसका डिस्प्ले और कैमरा कमाल का है!", "Hindi", "Positive"),
    ("बिल्कुल घटिया क्वालिटी है, एक दिन में ही काम करना बंद कर दिया। पैसे बर्बाद।", "Hindi", "Negative"),
    ("bahut accha product hai quality zabardast hai mujhe pasand aaya", "Hindi", "Positive"),
    ("kuch khaas nahi hai average product hai delivery late aayi", "Hindi", "Neutral"),
    ("bilkul ghatiya service hai return request accept nahi kar rahe", "Hindi", "Negative"),
    ("paisa vasool product hai, itne kam daam me itna accha phone mila", "Hindi", "Positive"),
    ("battery bahut jaldi khatam ho rahi hai aur charge bhi slow hota hai", "Hindi", "Negative"),
    ("पैकिंग बहुत अच्छी थी और डिलीवरी भी समय पर मिली। धन्यवाद!", "Hindi", "Positive"),
    ("डिलीवरी एजेंट का व्यवहार बहुत खराब था, पार्सल फेंक कर चला गया।", "Hindi", "Negative"),
    ("theek thaak hai daily use ke liye sahi hai", "Hindi", "Neutral"),
    ("kripya ye mat khareedo, nakli product bheja hai", "Hindi", "Negative"),
    ("sound quality ekdum mast hai bass bhi badhiya hai", "Hindi", "Positive"),
    ("स्क्रीन पर स्क्रैच थे जब बॉक्स खोला, बहुत निराश हुआ।", "Hindi", "Negative"),
    ("अच्छा अनुभव रहा, दोबारा जरूर खरीदूंगा।", "Hindi", "Positive"),
    ("camera theek hai lekin night mode me noise aati hai", "Hindi", "Neutral"),

    # Tamil
    ("இந்த மடிக்கணினி மிக விரைவாக வேலை செய்கிறது, தரம் அருமை.", "Tamil", "Positive"),
    ("மிகவும் மோசமான தயாரிப்பு, வாங்கிய மறுநாளே பழுதாகிவிட்டது.", "Tamil", "Negative"),
    ("romba nalla product, sound bass superaa irukku enakku romba pudichirukku", "Tamil", "Positive"),
    ("indha product seriyilla, rendu naal la odanju pochu kaasu veena pochu", "Tamil", "Negative"),
    ("paravala normal use ku nalla irukku delivery fast", "Tamil", "Neutral"),
    ("battery backup semma vera level, charge potta 2 days varudhu", "Tamil", "Positive"),
    ("customer care call panna eduka maatranga romba mosam", "Tamil", "Negative"),
    ("விலைக்கு தகுந்த தரம், மிக வேகமாக டெலிவரி செய்யப்பட்டது.", "Tamil", "Positive"),
    ("பேக்கேஜிங் சேதமடைந்துள்ளது, பொருள் வேலை செய்யவில்லை.", "Tamil", "Negative"),
    ("audio quality nalla irukku aana mic konjam slow", "Tamil", "Neutral"),
    ("super build quality brother, kandippa vaangalaam", "Tamil", "Positive"),
    ("chinna damage irundhadhu aana replacement pannitaanga", "Tamil", "Neutral"),
    ("வடிவமைப்பு மிகவும் அழகாக உள்ளது, பயன்பாடு எளிது.", "Tamil", "Positive"),
    ("சார்ஜர் பாக்ஸில் இல்லை, ஏமாற்றிவிட்டார்கள்.", "Tamil", "Negative"),
    ("worth for money, semma product", "Tamil", "Positive"),

    # Kannada
    ("ಈ ಉತ್ಪನ್ನ ತುಂಬಾ ಉಪಯುಕ್ತವಾಗಿದೆ ಮತ್ತು ಬೆಲೆಗೆ ತಕ್ಕ ಮೌಲ್ಯ ನೀಡುತ್ತದೆ.", "Kannada", "Positive"),
    ("ತುಂಬಾ ಕೆಟ್ಟ ಗುಣಮಟ್ಟ, ಒಂದು ವಾರದಲ್ಲೇ ಹಾಳಾಗಿದೆ, ಯಾರೂ ಕೊಳ್ಳಬೇಡಿ.", "Kannada", "Negative"),
    ("tumba chennagi ide product, naanu thumba khushi aagiddene", "Kannada", "Positive"),
    ("kettadu quality ide, charge aagalla waste of money", "Kannada", "Negative"),
    ("parvagilla sariyagide, casual use ge ok", "Kannada", "Neutral"),
    ("sound quality tumba chennagide, bass super aagide", "Kannada", "Positive"),
    ("service center response sari illa, tumba bejaar aaythu", "Kannada", "Negative"),
    ("ಡೆಲಿವರಿ ಬೇಗ ಬಂತು, ಪ್ಯಾಕಿಂಗ್ ಕೂಡ ಚೆನ್ನಾಗಿತ್ತು.", "Kannada", "Positive"),
    ("ಬಾಕ್ಸ್ ಒಡೆದಿತ್ತು, ಒಳಗಿನ ಸ್ಕ್ರೀನ್ ಸ್ಕ್ರ್ಯಾಚ್ ಆಗಿದೆ.", "Kannada", "Negative"),
    ("price ge taggante ide, average product", "Kannada", "Neutral"),
    ("tumba ishta aaythu, daily workouts ge tumba use aagide", "Kannada", "Positive"),
    ("mic voice clear illa, call maduvaga problem aagutte", "Kannada", "Negative"),
    ("ಬ್ಯಾಟರಿ ಬಾಳಿಕೆ ಅದ್ಭುತವಾಗಿದೆ, ೪೮ ಗಂಟೆ ಬರುತ್ತದೆ.", "Kannada", "Positive"),
    ("ಹಣ ವ್ಯರ್ಥ, ಕೆಲಸ ಮಾಡುವುದಿಲ್ಲ.", "Kannada", "Negative"),
    ("channagide buy madbahudu", "Kannada", "Positive"),

    # Malayalam
    ("valare nallathoru product aanu, njan fully satisfied aanu", "Malayalam", "Positive"),
    ("mosham quality, aarkkum recommend cheyyilla, cash poyi", "Malayalam", "Negative"),
    ("sound clarity adipoli aanu, battery life kollam", "Malayalam", "Positive"),
    ("oru divasam kondu damage aayi, service valare mosham", "Malayalam", "Negative"),
    ("valare nallath, price nu ullathu undu", "Malayalam", "Positive"),
    ("packaging potiyathanu kitiyathu, return koduthu", "Malayalam", "Negative"),
    ("kuzhappamilla, normal usage nu nannayi work cheyyunnu", "Malayalam", "Neutral"),
    ("ഇത് വളരെ മികച്ചതാണ്, ശബ്ദ നിലവാരം സൂപ്പർ.", "Malayalam", "Positive"),
    ("വളരെ മോശം അനുഭവം, വാറന്റി നൽകുന്നില്ല.", "Malayalam", "Negative"),
    ("battery backup kuravanu aanaal design nallathu", "Malayalam", "Neutral"),

    # Bengali
    ("khub bhalo product, shobai k kinte bolbo, oshadharon performence", "Bengali", "Positive"),
    ("ekdom baje quality, 2 din e nosto hoye gelo, taka nosto", "Bengali", "Negative"),
    ("dam onujayi etar sound quality khub sundor", "Bengali", "Positive"),
    ("delivery onek late koreche ar packaging o bhalo chilo na", "Bengali", "Negative"),
    ("চলনসই, খুব বেশি ভালোও না আবার খারাপও না।", "Bengali", "Neutral"),
    ("দারুণ ডিসপ্লে এবং ব্যাটারি ব্যাকআপ, আমি খুব খুশি।", "Bengali", "Positive"),
    ("একদম ভুয়ো জিনিস, কোনো কাজ করছে না।", "Bengali", "Negative"),
    ("khub shundor build quality, amar khub pochondo hoyeche", "Bengali", "Positive"),

    # Marathi
    ("khup chhan product ahe, mala khup aavadla ha phone", "Marathi", "Positive"),
    ("ekdum vait quality ahe, lavkarach kharab jhala", "Marathi", "Negative"),
    ("sound quality ekdum bhari ahe, bass pan chhan ahe", "Marathi", "Positive"),
    ("delivery khup late jhali, packing phutleli hoti", "Marathi", "Negative"),
    ("उत्पादन खूप चांगले आहे, किंमतही योग्य आहे.", "Marathi", "Positive"),
    ("एकदम बकवास उत्पादन, पैसे वाया गेले.", "Marathi", "Negative"),
    ("theek ahe, normal use sathi changla ahe", "Marathi", "Neutral"),
    ("battery backup changla ahe, 2 divas chalte", "Marathi", "Positive"),

    # English
    ("Exceptional build quality, stunning display and long battery life. 5 stars!", "English", "Positive"),
    ("Terrible experience. The item stopped working after 3 days. Complete scam.", "English", "Negative"),
    ("The delivery was on time. Performance is standard for this budget.", "English", "Neutral"),
    ("Customer support resolved my warranty claim within 24 hours. Great service!", "English", "Positive"),
    ("Packaging arrived soaked and crushed. The product inside was completely damaged.", "English", "Negative"),
    ("Camera is decent in daylight but struggles in low light. Decent purchase.", "English", "Neutral"),
    ("Fast charging is phenomenal, reaches 100% in 35 minutes.", "English", "Positive"),
    ("Horrible microphone quality during Zoom meetings, constant background static.", "English", "Negative"),
    ("Solid overall value for the discounted price. Recommended for students.", "English", "Positive"),
    ("Overheats drastically while multi-tasking. Very disappointed.", "English", "Negative"),
    ("Average battery backup, lasts around 6 hours on heavy screen time.", "English", "Neutral"),
    ("Premium glass back and smooth 120Hz refresh rate. Absolutely love it!", "English", "Positive"),
    ("Missing charging cable in the retail box. Seller refused to replace.", "English", "Negative"),
    ("Met all expectations for everyday browsing and media consumption.", "English", "Neutral"),
    ("Best purchase this year! Sound is crisp and noise cancellation works well.", "English", "Positive"),
]

def seed_database():
    print("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # 1. Create or get Demo User
        demo_email = "demo@example.com"
        user = db.query(User).filter(User.email == demo_email).first()
        if not user:
            print("Creating demo user: demo@example.com / demo1234")
            user = User(
                email=demo_email,
                hashed_password=hash_password("demo1234"),
                org_name="BharatRetail Analytics"
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            print(f"Demo user already exists (id={user.id}).")

        # 2. Create 3 Products
        product_names = [
            ("OnePlus Nord 3", "Smartphones"),
            ("Boat Airdopes 141", "Audio & Wearables"),
            ("Noise ColorFit Pulse", "Smartwatches")
        ]
        products = []
        for p_name, cat in product_names:
            p = db.query(Product).filter(Product.user_id == user.id, Product.name == p_name).first()
            if not p:
                p = Product(user_id=user.id, name=p_name, category=cat)
                db.add(p)
                db.commit()
                db.refresh(p)
            products.append(p)
        print(f"Ensured {len(products)} products exist.")

        # Check existing reviews count
        existing_rev_count = db.query(Review).filter(Review.user_id == user.id).count()
        if existing_rev_count >= 100:
            print(f"Database already contains {existing_rev_count} reviews for demo user. Skipping seed.")
            return

        print(f"Seeding ~120 reviews spread over 90 days...")
        now = datetime.now(timezone.utc)
        
        # We duplicate and jitter the pool to create ~125 reviews
        extended_pool = []
        while len(extended_pool) < 125:
            for item in REVIEWS_SEEDS:
                if len(extended_pool) >= 125:
                    break
                extended_pool.append(item)

        reviews_to_add = []
        for idx, (text, lang_hint, expected_sent) in enumerate(extended_pool):
            analysis = analyze_review(text)
            
            # Spread dates over past 90 days
            day_offset = random.randint(0, 89)
            hour_offset = random.randint(0, 23)
            review_date = now - timedelta(days=day_offset, hours=hour_offset)
            
            chosen_product = random.choice(products)
            import json

            rev = Review(
                user_id=user.id,
                product_id=chosen_product.id,
                original_text=analysis["original_text"],
                language=analysis["language"],
                script=analysis["script"],
                is_romanized=analysis["is_romanized"],
                transliterated_text=analysis["transliterated_text"],
                sentiment=analysis["sentiment"],
                confidence=analysis["confidence"],
                prob_pos=analysis["prob_pos"],
                prob_neg=analysis["prob_neg"],
                prob_neu=analysis["prob_neu"],
                aspects=json.dumps(analysis["aspects"]),
                source=random.choice(["web_form", "bulk_csv", "e-commerce_api"]),
                review_date=review_date,
                created_at=review_date
            )
            reviews_to_add.append(rev)

        db.add_all(reviews_to_add)
        db.commit()
        print(f"Successfully seeded {len(reviews_to_add)} reviews across 7+ Indian languages!")

    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
