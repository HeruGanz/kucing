from pyrogram import Client, filters
import asyncio
import re
import time

app = Client(
    "my_userbot.session",
    api_id=29933911,
    api_hash="7203358c613c038dbd69e84d969cc0bd"
)

# Global variables
target_group_id = None
delay_minutes = 1
broadcast_message = "Halo! Ini pesan dari bot 😉"  # Default message
sending_task = None
is_sending = False
start_time = None
sent_count = 0
failed_count = 0

async def extract_group_id(client, group_link):
    try:
        # Handle t.me/joinchat links (private groups with invite links)
        if "joinchat" in group_link:
            # Get the invite link hash
            hash_part = group_link.split("/")[-1]
            # Get chat object using the invite link
            chat = await app.get_chat(f"https://t.me/joinchat/{hash_part}")
            return chat.id
        
        # Handle regular t.me links (public groups)
        elif "t.me/" in group_link:
            # Get the username part
            username = group_link.split("t.me/")[-1].split("/")[0]
            if username.startswith("+"):
                username = username[1:]
            # Get chat object using the username
            chat = await app.get_chat(username)
            return chat.id
        
        # Handle numeric IDs (if someone still wants to use them)
        elif group_link.lstrip("-").isdigit():
            return int(group_link)
        
        return None
    except Exception as e:
        print(f"Error extracting group ID: {e}")
        return None

# Set target group using link
@app.on_message(filters.command("setgroup") & filters.me)
async def set_group(client, message):
    global target_group_id
    try:
        group_link = message.text.split(maxsplit=1)[1].strip()
        
        # Basic validation
        if not any(x in group_link for x in ["t.me/", "telegram.me/", "https://", "joinchat"]) and not group_link.lstrip("-").isdigit():
            await message.reply("❌ Format link tidak valid. Gunakan link grup Telegram atau ID grup.")
            return
            
        # Extract group ID
        group_id = await extract_group_id(client, group_link)
        
        if group_id:
            target_group_id = group_id
            await message.reply(f"✅ Target grup berhasil diset:\nID: `{target_group_id}`\nDari link: {group_link}")
        else:
            await message.reply("❌ Gagal mendapatkan ID grup. Pastikan link valid dan bot sudah join di grup tersebut.")
            
    except IndexError:
        await message.reply("❌ Format salah. Gunakan `/setgroup [link_grup]`\nContoh:\n`/setgroup https://t.me/namagrup`\n`/setgroup https://t.me/joinchat/xxxxxx`\n`/setgroup -1001234567890`")

# [Rest of your existing code remains the same...]

# Set delay between messages
@app.on_message(filters.command("setdelay") & filters.me)
async def set_delay(client, message):
    global delay_minutes
    try:
        delay_minutes = int(message.text.split(maxsplit=1)[1])
        if delay_minutes < 1:
            await message.reply("⚠️ Delay minimal 1 menit")
            return
        await message.reply(f"✅ Delay diatur ke {delay_minutes} menit.")
    except (IndexError, ValueError):
        await message.reply("❌ Format salah. Gunakan `/setdelay [menit]`\nContoh: `/setdelay 5`")

# Set broadcast message
@app.on_message(filters.command("setmsg") & filters.me)
async def set_message(client, message):
    global broadcast_message
    try:
        broadcast_message = message.text.split(maxsplit=1)[1]
        await message.reply(f"✅ Pesan broadcast disimpan:\n\n{broadcast_message}")
    except IndexError:
        await message.reply("❌ Format salah. Gunakan `/setmsg [pesan]`\nContoh: `/setmsg Halo! Ini pesan broadcast`")

# Check status
@app.on_message(filters.command("status") & filters.me)
async def check_status(client, message):
    global start_time, sent_count, failed_count
    
    status = "🟢 Sedang aktif mengirim" if is_sending else "🔴 Tidak aktif"
    current_time = time.strftime("%H:%M:%S", time.localtime())
    
    if is_sending and start_time:
        elapsed_time = time.time() - start_time
        hours, remainder = divmod(elapsed_time, 3600)
        minutes, seconds = divmod(remainder, 60)
        runtime = f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
    else:
        runtime = "Tidak aktif"
    
    status_message = (
        f"📊 **Status Broadcast**\n"
        f"• Status: {status}\n"
        f"• Grup Target: `{target_group_id or 'Belum diset'}`\n"
        f"• Delay: {delay_minutes} menit\n"
        f"• Runtime: {runtime}\n"
        f"• Sukses: {sent_count}\n"
        f"• Gagal: {failed_count}\n"
        f"• Pesan: {broadcast_message[:50]}..."
    )
    await message.reply(status_message)

# Stop sending
@app.on_message(filters.command("stopsend") & filters.me)
async def stop_send(client, message):
    global sending_task, is_sending, start_time
    if sending_task:
        sending_task.cancel()
        sending_task = None
        is_sending = False
        start_time = None
        await message.reply("⛔ Pengiriman dihentikan!")
    else:
        await message.reply("❗ Tidak ada pengiriman aktif.")

# Start sending
@app.on_message(filters.command("startsend") & filters.me)
async def start_send(client, message):
    global sending_task, is_sending, start_time, sent_count, failed_count

    if not target_group_id:
        await message.reply("❗ Set grup target dulu dengan `/setgroup`")
        return

    if is_sending:
        await message.reply("⚠️ Masih mengirim. Hentikan dulu dengan `/stopsend`")
        return

    async def send_dm_to_users():
        global is_sending, start_time, sent_count, failed_count
        is_sending = True
        start_time = time.time()
        sent_count = 0
        failed_count = 0
        
        try:
            await message.reply(f"🚀 Memulai broadcast ke grup {target_group_id}...")
            
            async for member in app.get_chat_members(target_group_id):
                if not is_sending:  # Stop if sending was cancelled
                    break
                    
                user_id = member.user.id
                try:
                    if not member.user.is_bot:  # Skip bots
                        await app.send_message(user_id, broadcast_message)
                        sent_count += 1
                        await asyncio.sleep(delay_minutes * 60)
                except Exception as e:
                    failed_count += 1
                    print(f"Gagal mengirim ke {user_id}: {str(e)}")
                    
            if is_sending:  # Only send completion message if not stopped manually
                await message.reply(
                    f"✅ Broadcast selesai!\n"
                    f"• Sukses: {sent_count}\n"
                    f"• Gagal: {failed_count}\n"
                    f"• Total: {sent_count + failed_count}"
                )
        except Exception as e:
            await message.reply(f"❌ Terjadi error: {str(e)}")
        finally:
            is_sending = False
            start_time = None

    sending_task = asyncio.create_task(send_dm_to_users())

app.run()