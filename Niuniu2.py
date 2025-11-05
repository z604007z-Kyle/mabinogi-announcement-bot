import discord
import asyncio
import yt_dlp
import requests
import re
import time
from discord.ext import commands, tasks
from discord.ui import View, Button
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
from datetime import time as dtime
import pytz # type: ignore

# 載入環境變數
load_dotenv()
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
WEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5/forecast"

# Debug 環境變數
print("DISCORD_BOT_TOKEN:", os.getenv("DISCORD_BOT_TOKEN"))
print("WEATHER_API_KEY:", os.getenv("WEATHER_API_KEY"))

# 設定 bot
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# 用來記錄上次發送的資料，防止重複發送
last_data = {}

# 設定爬蟲功能
def fetch_data():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    url = "https://tw.nexon.com/mh/zh/home/bulletin/0/"
    driver.get(url)
    time.sleep(3)

    result = {}
    try:
        title_element = driver.find_element(By.CSS_SELECTOR, ".newslist__item-title")
        result['title'] = title_element.text
    except Exception as e:
        result['title'] = "未找到目標標題"

    try:
        date_element = driver.find_element(By.CSS_SELECTOR, ".newslist__item-date")
        result['date'] = date_element.text
    except Exception as e:
        result['date'] = "未找到目標日期"

    try:
        wait = WebDriverWait(driver, 10)
        more_button = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "morearrow__inner")))
        ActionChains(driver).move_to_element(more_button).click().perform()
        time.sleep(3)
        result['more_url'] = driver.current_url
    except Exception as e:
        print("發生錯誤:", e)
        result['more_url'] = "未能獲取新網址"

    try:
        img_element = driver.find_element(By.CSS_SELECTOR, ".newslist__item-img")
        img_url = img_element.value_of_css_property("background-image")
        img_url = img_url.split('url("')[1].split('")')[0]
        result['img_url'] = img_url
    except Exception as e:
        result['img_url'] = "未找到圖片 URL"

    driver.quit()
    return result

# 定義定時任務（每 5 分鐘執行一次）
@tasks.loop(minutes=5)
async def fetch_and_send_data():
    data = await asyncio.to_thread(fetch_data)
    global last_data
    if data['title'] != last_data.get('title', '') or data['date'] != last_data.get('date', ''):
        channel_id = 1286668475997356155
        channel = bot.get_channel(channel_id)
        if channel:
            embed = discord.Embed(
                title=data['title'],
                description=f"日期： {data['date']}\n {data['more_url']}",
                color=discord.Color.green()
            )
            if data['img_url'] != "未找到圖片 URL":
                embed.set_image(url=data['img_url'])
            await channel.send(embed=embed)
            last_data = data
    else:
        print("沒有新資料，未發送訊息。")

# 每日早上 9 點天氣推送
# @tasks.loop(hours=24)
# async def send_daily_weather():
#     taipei_tz = pytz.timezone("Asia/Taipei")
#     now = datetime.now(taipei_tz)
#     target_time = dtime(9, 0)
#     if now.hour == target_time.hour and now.minute < 5:
#         if not WEATHER_API_KEY:
#             print("WEATHER_API_KEY 未設置，無法推送天氣更新")
#             return
#         channel_id = 1286668475997356155
#         channel = bot.get_channel(channel_id)
#         if channel:
#             params = {
#                 "q": "Taipei,TW",
#                 "units": "metric",
#                 "lang": "zh_tw",
#                 "appid": WEATHER_API_KEY
#             }
#             try:
#                 response = await asyncio.to_thread(requests.get, WEATHER_BASE_URL, params=params)
#                 data = response.json()
#                 if response.status_code == 200:
#                     # 選擇最接近當前時間的時段
#                     current_timestamp = int(now.timestamp())
#                     closest_forecast = min(data["list"], key=lambda x: abs(x["dt"] - current_timestamp))
#                     weather = closest_forecast["weather"][0]["description"]
#                     temp = closest_forecast["main"]["temp"]
#                     feels_like = closest_forecast["main"]["feels_like"]
#                     humidity = closest_forecast["main"]["humidity"]
#                     wind_speed = closest_forecast["wind"]["speed"]
#                     pop = closest_forecast.get("pop", 0) * 100
#                     city_name = data["city"]["name"]
#                     icon = closest_forecast["weather"][0]["icon"]
#                     weather_main = closest_forecast["weather"][0]["main"].lower()
#                     # 計算預報時段
#                     forecast_time = datetime.fromtimestamp(closest_forecast["dt"], tz=taipei_tz)
#                     forecast_end_time = forecast_time + timedelta(hours=3)
#                     time_range = f"{forecast_time.strftime('%H:%M')}-{forecast_end_time.strftime('%H:%M')}"

#                     # 動態顏色
#                     color = discord.Color.blue()
#                     if "clear" in weather_main:
#                         color = 0xFFFF00  # 黃色（晴天）
#                     elif "clouds" in weather_main:
#                         color = 0x808080  # 灰色（多雲）
#                     elif "rain" in weather_main or "drizzle" in weather_main:
#                         color = 0x0000FF  # 藍色（雨天）

#                     embed = discord.Embed(
#                         title=f"🌆 {city_name} 每日天氣更新",
#                         color=color,
#                         timestamp=now
#                     )
#                     embed.add_field(
#                         name="🌤️ 當前天氣",
#                         value=weather,
#                         inline=False
#                     )
#                     embed.add_field(
#                         name="詳細資訊",
#                         value=f"🌡️ 溫度：{temp}°C (體感 {feels_like}°C)\n"
#                               f"💧 濕度：{humidity}%\n"
#                               f"💨 風速：{wind_speed} m/s\n"
#                               f"☔ 降雨機率：{pop}% ({time_range})",
#                         inline=False
#                     )
#                     embed.set_thumbnail(url=f"https://openweathermap.org/img/wn/{icon}@2x.png")
#                     await channel.send(embed=embed)
#                 else:
#                     error_message = data.get("message", "未知錯誤")
#                     print(f"每日天氣推送失敗：{error_message}")
#             except Exception as e:
#                 print(f"每日天氣推送錯誤: {e}")

# @send_daily_weather.before_loop
# async def before_send_daily_weather():
#     await bot.wait_until_ready()
#     taipei_tz = pytz.timezone("Asia/Taipei")
#     now = datetime.now(taipei_tz)
#     next_run = now.replace(hour=9, minute=0, second=0, microsecond=0)
#     if now.hour >= 9:
#         next_run = next_run + timedelta(days=1)
#     seconds_until_next_run = (next_run - now).total_seconds()
#     await asyncio.sleep(seconds_until_next_run)

# 天氣查詢功能
# @bot.command()
# async def weather(ctx, *, query: str):
#     """查詢指定城市或經緯度的天氣資訊。格式：!weather 城市名稱 或 !weather lat=緯度,lon=經度"""
#     if not WEATHER_API_KEY:
#         await ctx.send("天氣 API Key 未設置，請聯繫管理員！")
#         return

#     try:
#         city_map = {
#             "台北": "Taipei,TW",
#             "台中": "Taichung,TW",
#             "高雄": "Kaohsiung,TW"
#         }
#         lat_lon_match = re.match(r"lat=([\d.-]+),lon=([\d.-]+)", query.strip())
#         params = {
#             "units": "metric",
#             "lang": "zh_tw",
#             "appid": WEATHER_API_KEY
#         }

#         if lat_lon_match:
#             params["lat"] = float(lat_lon_match.group(1))
#             params["lon"] = float(lat_lon_match.group(2))
#         else:
#             query = query.strip()
#             params["q"] = city_map.get(query, query)

#         response = await asyncio.to_thread(requests.get, WEATHER_BASE_URL, params=params)
#         data = response.json()

#         if response.status_code == 200:
#             # 選擇最接近當前時間的時段
#             taipei_tz = pytz.timezone("Asia/Taipei")
#             current_timestamp = int(datetime.now(taipei_tz).timestamp())
#             closest_forecast = min(data["list"], key=lambda x: abs(x["dt"] - current_timestamp))
#             weather = closest_forecast["weather"][0]["description"]
#             temp = closest_forecast["main"]["temp"]
#             feels_like = closest_forecast["main"]["feels_like"]
#             humidity = closest_forecast["main"]["humidity"]
#             wind_speed = closest_forecast["wind"]["speed"]
#             pop = closest_forecast.get("pop", 0) * 100
#             city_name = data["city"]["name"]
#             icon = closest_forecast["weather"][0]["icon"]
#             weather_main = closest_forecast["weather"][0]["main"].lower()
#             # 計算預報時段
#             forecast_time = datetime.fromtimestamp(closest_forecast["dt"], tz=taipei_tz)
#             forecast_end_time = forecast_time + timedelta(hours=3)
#             time_range = f"{forecast_time.strftime('%H:%M')}-{forecast_end_time.strftime('%H:%M')}"

#             # 動態顏色
#             color = discord.Color.blue()
#             if "clear" in weather_main:
#                 color = 0xFFFF00  # 黃色（晴天）
#             elif "clouds" in weather_main:
#                 color = 0x808080  # 灰色（多雲）
#             elif "rain" in weather_main or "drizzle" in weather_main:
#                 color = 0x0000FF  # 藍色（雨天）

#             embed = discord.Embed(
#                 title=f"🌆 {city_name} 的天氣資訊",
#                 color=color
#             )
#             embed.add_field(
#                 name="🌤️ 當前天氣",
#                 value=weather,
#                 inline=False
#             )
#             embed.add_field(
#                 name="詳細資訊",
#                 value=f"🌡️ 溫度：{temp}°C (體感 {feels_like}°C)\n"
#                       f"💧 濕度：{humidity}%\n"
#                       f"💨 風速：{wind_speed} m/s\n"
#                       f"☔ 降雨機率：{pop}% ({time_range})",
#                 inline=False
#             )
#             embed.set_thumbnail(url=f"https://openweathermap.org/img/wn/{icon}@2x.png")
#             await ctx.send(embed=embed)
#         else:
#             error_message = data.get("message", "未知錯誤")
#             if "Invalid API key" in error_message:
#                 await ctx.send("無效的 API Key，請聯繫管理員檢查 WEATHER_API_KEY！")
#             else:
#                 await ctx.send(f"無法獲取天氣資訊：{error_message}。請檢查輸入（城市名稱如 '台北' 或 'Taipei,TW'，或 lat=緯度,lon=經度）。")
#     except ValueError:
#         await ctx.send("經緯度格式錯誤，請使用正確格式：lat=緯度,lon=經度（例如 lat=25.0330,lon=121.5654）")
#     except Exception as e:
#         await ctx.send("發生錯誤，請稍後再試！")
#         print(f"天氣查詢錯誤: {e}")

# 用來管理音樂播放
voice_clients = {}
queue = {}
song_messages = {}

class MusicPlayerView(View):
    def __init__(self, ctx):
        super().__init__(timeout=None)
        self.ctx = ctx

    @discord.ui.button(label="▶▶", style=discord.ButtonStyle.primary, custom_id="next_song")
    async def next_song(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        await skip(self.ctx)

@bot.command()
async def play(ctx, url: str):
    """ 播放 YouTube 音樂 或 播放清單 """
    if ctx.author != bot.user:
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass

    guild_id = ctx.guild.id
    if guild_id not in voice_clients:
        await ctx.invoke(join)
    if guild_id not in queue:
        queue[guild_id] = []

    if "playlist?list=" in url:
        videos = await get_playlist_videos(url)
        if not videos:
            await ctx.send("無法解析播放清單！")
            return
        queue[guild_id].extend(videos)
    else:
        queue[guild_id].append(url)

    if not voice_clients[guild_id].is_playing():
        await play_next(ctx)

async def play_next(ctx):
    guild_id = ctx.guild.id
    if guild_id not in queue or not queue[guild_id]:
        if guild_id in song_messages and song_messages[guild_id]:
            try:
                await song_messages[guild_id].edit(content="🎵 播放完成！沒有更多歌曲。")
            except discord.NotFound:
                pass
        return

    next_url = queue[guild_id].pop(0)
    await play_video(ctx, next_url)

async def play_video(ctx, url):
    guild_id = ctx.guild.id
    voice_client = voice_clients[guild_id]

    ydl_opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "noplaylist": True,
        "socket_timeout": 60,
    }

    loop = asyncio.get_event_loop()
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))
            audio_url = info['url']
            title = info['title']

        if voice_client.is_playing():
            voice_client.stop()

        def after_play(error):
            if error:
                print(f"播放時發生錯誤: {error}")
            asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)

        voice_client.play(discord.FFmpegPCMAudio(audio_url, before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"), after=after_play)

        view = MusicPlayerView(ctx)
        if guild_id in song_messages and song_messages[guild_id]:
            try:
                await song_messages[guild_id].edit(content=f"🎵 正在播放: {title}", view=view)
            except discord.NotFound:
                song_messages[guild_id] = await ctx.send(f"🎵 正在播放: {title}", view=view)
        else:
            song_messages[guild_id] = await ctx.send(f"🎵 正在播放: {title}", view=view)
    except Exception as e:
        await ctx.send(f"播放音樂時發生錯誤: {e}")
        print(f"Error: {e}")

async def get_playlist_videos(url):
    ydl_opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "extract_audio": True,
        "force_generic_extractor": True,
    }
    loop = asyncio.get_event_loop()
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))
            if 'entries' in info:
                return [entry['url'] for entry in info['entries'] if 'url' in entry]
            return []
    except Exception as e:
        print(f"Error extracting playlist: {e}")
        return []

@bot.command()
async def join(ctx):
    """ 加入語音頻道 """
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        voice_client = await channel.connect()
        voice_clients[ctx.guild.id] = voice_client
        queue[ctx.guild.id] = []
    else:
        await ctx.send("請先加入語音頻道！")

@bot.command()
async def leave(ctx):
    """ 離開語音頻道 """
    guild_id = ctx.guild.id
    if guild_id in voice_clients:
        await voice_clients[guild_id].disconnect()
        del voice_clients[guild_id]
        queue.pop(guild_id, None)

@bot.command()
async def skip(ctx):
    """ 播放下一首音樂 """
    guild_id = ctx.guild.id
    if guild_id in voice_clients and queue.get(guild_id):
        voice_clients[guild_id].stop()
    else:
        await ctx.send("隊列中沒有更多歌曲！")

@bot.event
async def on_ready():
    print(f'已成功登入為 {bot.user}!')
    if not fetch_and_send_data.is_running():
        fetch_and_send_data.start()
    # if not send_daily_weather.is_running():
    #     send_daily_weather.start()

token = os.getenv("DISCORD_BOT_TOKEN")
if not token:
    raise ValueError("DISCORD_BOT_TOKEN 未設置或無效")
bot.run(token)