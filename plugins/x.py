from run import Button, BotState
from utils import lru_cache
from utils import os, hashlib, re, asyncio
from utils import db, bs4, aiohttp
from utils import TweetCapture

class X:
    
    @classmethod
    def initialize(cls):
        cls.screen_shot_path = 'repository/ScreenShots'
        if not os.path.isdir(cls.screen_shot_path):
            os.makedirs(cls.screen_shot_path, exist_ok=True)
        
    @lru_cache(maxsize=128)  # Cache the last 128 screenshots
    def get_screenshot_path(tweet_url):
        url_hash = hashlib.blake2b(tweet_url.encode()).hexdigest()
        filename = f"{url_hash}.png"
        return os.path.join(X.screen_shot_path, filename)

    @staticmethod
    async def take_screenshot_of_tweet(event, tweet_url):
        tweet_message = await event.respond("Processing your request ...\nPlease wait while the screenshot is being generated.\nThis may take a few moments.")

        settings = await TweetCapture.get_settings(event.sender_id)
        night_mode = settings['night_mode']
        
        screenshot_path = X.get_screenshot_path(tweet_url+night_mode)

        if os.path.exists(screenshot_path):
            await tweet_message.delete()
            return screenshot_path
        try:
            screenshot_task = asyncio.create_task(TweetCapture.screenshot(tweet_url, screenshot_path, night_mode))
            await screenshot_task
            
            await tweet_message.delete()
            return screenshot_path
        
        except Exception as Err:
            await tweet_message.edit(f"We apologize for the inconvenience.\nThe requested tweet could not be found. Reason: {str(Err)}")
            return None

    @staticmethod
    async def send_screenshot(client, event, screenshot_path, has_media) -> bool:
        screen_shot_message = await event.respond("Uploading the screenshot. Please stand by...")
        button = Button.inline("Download Media", data=b"plugin/X/download_media") if has_media else None
        
        prev_screen_shot = await BotState.get_tweet_screenshot(event.sender_id)
        try:
            await prev_screen_shot.edit(buttons=None)
        except:
            pass
        
        try:
            screen_shot = await client.send_file(
                event.chat_id,
                screenshot_path,
                caption="Here is the requested tweet screenshot.",
                buttons=button
            )
            await screen_shot_message.delete()
            
            await BotState.set_tweet_screenshot(event.sender_id, screen_shot)
            return True
        except:
            return False

    @staticmethod   
    def contains_x_or_twitter_link(text):
        pattern = r'(https?://(?:www\.)?twitter\.com/[^/\s]+/status/\d+|https?://(?:www\.)?x\.com/[^/\s]+)'
        return bool(re.search(pattern, text))
 
    @staticmethod   
    def find_and_send_x_or_twitter_link(text):
        pattern = r'(https?://(?:www\.)?twitter\.com/[^/\s]+/status/\d+|https?://(?:www\.)?x\.com/[^?\s]+)'
        match = re.search(pattern, text)
        return match.group(0) if match else None

    @staticmethod
    def normalize_url(link):
        if "x.com" in link:
            return link.replace("x.com", "fxtwitter.com")
        elif "twitter.com" in link:
            return link.replace("twitter.com", "fxtwitter.com")
        return link

    @staticmethod
    async def has_media(link):
        normalized_link = X.normalize_url(link)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(normalized_link) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = bs4.BeautifulSoup(html, "lxml")
                        meta_tag = soup.find("meta", attrs={"property": "og:video"})
                        if meta_tag:
                            return True
                        meta_tag = soup.find("meta", attrs={"property": "og:image"})
                        if meta_tag:
                            return True
                        return False
                    else:
                        print(f"Error fetching URL: {normalized_link} (status code: {response.status})")
                        return False

        except Exception as e:
            print(f"Error checking media in URL: {e}")
            return False
            
    async def fetch_media_url(link):
        normalized_link = X.normalize_url(link)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(normalized_link) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = bs4.BeautifulSoup(html, "lxml")
                        meta_tag = soup.find("meta", attrs={"property": "og:video"})
                        if meta_tag:
                            return meta_tag['content']
                        meta_tag = soup.find("meta", attrs={"property": "og:image"})
                        if meta_tag:
                            return meta_tag['content']
        except Exception as e:
            print(f"Error fetching media URL: {e}")
        return None

    @staticmethod
    async def download(client, event):
        user_id = event.sender_id
        link = await db.get_tweet_url(user_id)
        media_url = await X.fetch_media_url(link)

        if media_url:
            try:
                upload_message = await event.reply("Uploading Media ... Please hold on.")
                await client.send_file(event.chat_id, media_url, caption="Thank you for using - @Spotify_YT_Downloader_Bot")
                await upload_message.delete()
            except Exception as e:
                print(f"Error sending file: {e}")
                await event.reply("Oops Invalid link or Media Is Not Available :(")
        else:
            await event.reply("Oops Invalid link or Media Is Not Available :(")