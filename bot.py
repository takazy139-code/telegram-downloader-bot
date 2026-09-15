# --- HANDLE LINKS & MESSAGES ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    
    if text.startswith("http://") or text.startswith("https://"):
        await update.message.reply_text("⏳ កំពុងទាញយកវីដេអូ និងបង្កើត AI Caption ជូន, សូមរង់ចាំបន្តិច...")
        
        # កំណត់ yt-dlp options ជាមួយ player_client ដើម្បីបំបែកការទប់ស្កាត់របស់ YouTube
        ydl_opts = {
            'format': 'best',
            'outtmpl': 'downloads/%(id)s.%(ext)s',
            'max_filesize': 50 * 1024 * 1024,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web']
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
            
            with open(filename, 'rb') as video_file:
                await update.message.reply_video(
                    video=video_file,
                    caption=f"🎥 **{title}**\n\n{ai_caption}",
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
