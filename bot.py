import os
import logging
from google import genai
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from flask import Flask
from threading import Thread
import yt_dlp

# --- FLASK WEB SERVER ---
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 All-in-One Video Downloader & AI Bot is running 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# --- CONFIGURATIONS ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not TELEGRAM_BOT_TOKEN or not GEMINI_API_KEY:
    raise ValueError("❌ សូមកំណត់ TELEGRAM_BOT_TOKEN និង GEMINI_API_KEY ក្នុង Environment Variables ជាមុនសិន!")

client = genai.Client(api_key=GEMINI_API_KEY)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- /start COMMAND ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 សួស្តី! ខ្ញុំជា All-in-One Media Downloader & AI Bot.\n\n"
        "📥 **វិធីប្រើប្រាស់៖**\n"
        "គ្រាន់តែផ្ញើ Link (TikTok, YouTube, Facebook, Instagram) មកទីនេះ ខ្ញុំនឹងធ្វើការ៖\n"
        "1️⃣ ទាញយកវីដេអូជូនអ្នក (HD គ្មានសញ្ញាទឹក)\n"
        "2️⃣ បង្កើត Caption ខ្លីទាក់ទាញ និង Hashtag ស្វ័យប្រវត្តិដោយ AI!\n\n"
        "🎵 **ទាញយកជាសំឡេង៖**\n"
        "ប្រើពាក្យបញ្ជា `/mp3 [Link]` ដើម្បីបម្លែងជា MP3"
    )

# --- GEMINI AI CAPTION GENERATOR (Fixed short length for Telegram) ---
def generate_ai_caption(video_title: str, platform: str) -> str:
    try:
        prompt = (
            f"Write a very short social media caption and 3 popular hashtags "
            f"for a {platform} video titled: '{video_title}'. Keep it under 200 characters."
        )
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=prompt,
        )
        return response.text
    except Exception as e:
        return f"📌 វីដេអូ៖ {video_title}\n#Video #Trending"

# --- HANDLE LINKS & MESSAGES ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    
    if text.startswith("http://") or text.startswith("https://"):
        await update.message.reply_text("⏳ កំពុងទាញយកវីដេអូ និងបង្កើត AI Caption ជូន, សូមរង់ចាំបន្តិច...")
        
ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': 'downloads/%(id)s.%(ext)s',
            'max_filesize': 50 * 1024 * 1024,
            'extractor_args': {
                'youtube': {
                    'player_client': ['ios', 'mweb']  # ប្រើ ios និង mobile web ដើម្បីចៀសវាង Bot Check
                }
            },
        }
        
        try:
            os.makedirs("downloads", exist_ok=True)
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(text, download=True)
                filename = ydl.prepare_filename(info)
                title = info.get('title', 'Downloaded Video')
                extractor = info.get('extractor', 'Social Media')

            ai_caption = generate_ai_caption(title, extractor)
            
            # Safe truncation to strictly comply with Telegram's 1024 caption limit
            caption_text = f"🎥 **{title}**\n\n{ai_caption}"
            if len(caption_text) > 1024:
                caption_text = caption_text[:1021] + "..."

            with open(filename, 'rb') as video_file:
                await update.message.reply_video(
                    video=video_file,
                    caption=caption_text,
                    parse_mode="Markdown"
                )
            
            if os.path.exists(filename):
                os.remove(filename)
                
        except Exception as e:
            await update.message.reply_text(f"❌ មិនអាចទាញយកវីដេអូនេះបានទេ (វីដេអូធំពេក ឬជាប់សិទ្ធិ): {str(e)}")
    else:
        try:
            response = client.models.generate_content(
                model='gemini-3.6-flash',
                contents=text,
            )
            await update.message.reply_text(response.text)
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")

# --- /mp3 COMMAND ---
async def mp3_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ សូមដាក់ Link មកជាមួយផង! ឧទាហរណ៍៖ `/mp3 https://youtube.com/...`")
        return
    
    url = context.args[0]
    await update.message.reply_text("⏳ កំពុងបម្លែងជាសំឡេង MP3, សូមរង់ចាំបន្តិច...")
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web']
            }
        },
    }
    
    try:
        os.makedirs("downloads", exist_ok=True)
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            title = info.get('title', 'Audio')

        with open(filename, 'rb') as audio_file:
            await update.message.reply_audio(audio=audio_file, caption=f"🎵 {title}")
            
        if os.path.exists(filename):
            os.remove(filename)
    except Exception as e:
        await update.message.reply_text(f"❌ មានបញ្ហាក្នុងការទាញយក MP3: {str(e)}")

# --- MAIN FUNCTION ---
def main():
    t = Thread(target=run_flask)
    t.start()

    app_bot = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("mp3", mp3_command))
    app_bot.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    print("🤖 All-in-One Bot is polling...")
    app_bot.run_polling()

if __name__ == '__main__':
    main()
