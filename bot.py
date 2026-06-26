import discord
from discord.ext import commands
import aiohttp
import json
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
ADMIN_ID = 1512658477841908015

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix='/', intents=intents)

# Lưu trạng thái fake của các user
fake_status = {}

@bot.event
async def on_ready():
    print(f'Bot đã sẵn sàng! Logged in as {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f"Đã sync {len(synced)} lệnh slash")
    except Exception as e:
        print(e)

@bot.tree.command(name="fake", description="Fake theo user khác (Chỉ admin)")
async def fake(interaction: discord.Interaction, user_id: str):
    # Kiểm tra admin
    if interaction.user.id != ADMIN_ID:
        await interaction.response.send_message("❌ Bạn không có quyền sử dụng lệnh này!", ephemeral=True)
        return

    try:
        user_id_int = int(user_id)
    except ValueError:
        await interaction.response.send_message("❌ ID user không hợp lệ!", ephemeral=True)
        return

    # Tìm user trong server
    target_user = interaction.guild.get_member(user_id_int)
    if not target_user:
        await interaction.response.send_message("❌ Không tìm thấy user trong server!", ephemeral=True)
        return

    # Lấy thông tin user
    try:
        avatar_url = target_user.display_avatar.url
        username = target_user.name
        display_name = target_user.display_name
    except:
        await interaction.response.send_message("❌ Không thể lấy thông tin user!", ephemeral=True)
        return

    # Lưu trạng thái fake
    fake_status[interaction.guild.id] = {
        'user_id': user_id_int,
        'username': username,
        'display_name': display_name,
        'avatar_url': avatar_url,
        'active': True
    }

    embed = discord.Embed(
        title="✅ Đã bật chế độ fake!",
        description=f"Đang fake theo: {display_name} ({username})",
        color=discord.Color.green()
    )
    embed.set_thumbnail(url=avatar_url)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="stop_fake", description="Dừng fake (Chỉ admin)")
async def stop_fake(interaction: discord.Interaction):
    if interaction.user.id != ADMIN_ID:
        await interaction.response.send_message("❌ Bạn không có quyền sử dụng lệnh này!", ephemeral=True)
        return

    if interaction.guild.id in fake_status:
        fake_status[interaction.guild.id]['active'] = False
        await interaction.response.send_message("✅ Đã tắt chế độ fake!", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Chưa có chế độ fake nào được kích hoạt!", ephemeral=True)

@bot.event
async def on_message(message):
    # Bỏ qua tin nhắn của bot
    if message.author.bot:
        return

    # Bỏ qua tin nhắn trong DM
    if not message.guild:
        return

    # Kiểm tra fake status
    if message.guild.id not in fake_status:
        return

    status = fake_status[message.guild.id]
    if not status['active']:
        return

    # Nếu tin nhắn từ target user
    if message.author.id == status['user_id']:
        # Lấy channel để fake
        channel = message.channel
        
        # Tạo webhook hoặc gửi tin nhắn
        try:
            # Lấy webhook có sẵn hoặc tạo mới
            webhooks = await channel.webhooks()
            webhook = None
            
            for wh in webhooks:
                if wh.name == "FakeBotWebhook":
                    webhook = wh
                    break
            
            if not webhook:
                webhook = await channel.create_webhook(name="FakeBotWebhook")
            
            # Nội dung tin nhắn
            content = message.content
            files = []
            
            # Xử lý attachments (ảnh, file)
            if message.attachments:
                for attachment in message.attachments:
                    # Tải file
                    async with aiohttp.ClientSession() as session:
                        async with session.get(attachment.url) as resp:
                            if resp.status == 200:
                                file_data = await resp.read()
                                files.append((attachment.filename, file_data))
            
            # Gửi tin nhắn fake
            await webhook.send(
                content=content if content else None,
                username=status['display_name'],
                avatar_url=status['avatar_url'],
                files=[discord.File(fp=file_data, filename=filename) for filename, file_data in files] if files else None
            )
            
        except Exception as e:
            print(f"Lỗi khi gửi tin nhắn fake: {e}")
            await channel.send(f"⚠️ Lỗi fake message: {str(e)[:100]}")

    # Xử lý lệnh prefix nếu có
    await bot.process_commands(message)

# Lệnh test
@bot.tree.command(name="test", description="Test bot")
async def test(interaction: discord.Interaction):
    await interaction.response.send_message("Bot đang hoạt động!", ephemeral=True)

if __name__ == "__main__":
    if not TOKEN:
        print("❌ Vui lòng set DISCORD_TOKEN trong environment variables!")
        exit(1)
    bot.run(TOKEN)
