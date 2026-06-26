import discord
from discord.ext import commands
import aiohttp
import os
import sys
from dotenv import load_dotenv

# Fix lỗi audioop bằng cách ghi đè
try:
    import audioop
except ImportError:
    # Tạo audioop giả để tránh lỗi
    import builtins
    class MockAudioop:
        def __getattr__(self, name):
            return lambda *args, **kwargs: None
    builtins.__dict__['audioop'] = MockAudioop()

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
ADMIN_ID = 1512658477841908015

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix='/', intents=intents)

# Lưu trạng thái fake
fake_status = {}

@bot.event
async def on_ready():
    print(f'✅ Bot đã sẵn sàng! Logged in as {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f"✅ Đã sync {len(synced)} lệnh slash")
    except Exception as e:
        print(f"❌ Lỗi sync lệnh: {e}")

@bot.tree.command(name="fake", description="Fake theo user khác (Chỉ admin)")
async def fake(interaction: discord.Interaction, user_id: str):
    if interaction.user.id != ADMIN_ID:
        await interaction.response.send_message("❌ Bạn không có quyền sử dụng lệnh này!", ephemeral=True)
        return

    try:
        user_id_int = int(user_id)
    except ValueError:
        await interaction.response.send_message("❌ ID user không hợp lệ!", ephemeral=True)
        return

    target_user = interaction.guild.get_member(user_id_int)
    if not target_user:
        await interaction.response.send_message("❌ Không tìm thấy user trong server!", ephemeral=True)
        return

    try:
        avatar_url = target_user.display_avatar.url
        username = target_user.name
        display_name = target_user.display_name
    except:
        await interaction.response.send_message("❌ Không thể lấy thông tin user!", ephemeral=True)
        return

    fake_status[interaction.guild.id] = {
        'user_id': user_id_int,
        'username': username,
        'display_name': display_name,
        'avatar_url': avatar_url,
        'active': True
    }

    embed = discord.Embed(
        title="✅ Đã bật chế độ fake!",
        description=f"Đang fake theo: **{display_name}** ({username})",
        color=discord.Color.green()
    )
    embed.set_thumbnail(url=avatar_url)
    embed.add_field(name="User ID", value=f"`{user_id_int}`", inline=False)
    embed.add_field(name="Hướng dẫn", value="Bot sẽ tự động fake tất cả tin nhắn mới của user này", inline=False)
    
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

async def get_or_create_webhook(channel):
    """Lấy webhook có sẵn hoặc tạo mới"""
    webhooks = await channel.webhooks()
    
    for wh in webhooks:
        if wh.name == "FakeBotWebhook":
            return wh
    
    webhook = await channel.create_webhook(name="FakeBotWebhook")
    return webhook

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if not message.guild:
        return

    if message.guild.id not in fake_status:
        await bot.process_commands(message)
        return

    status = fake_status[message.guild.id]
    if not status['active']:
        await bot.process_commands(message)
        return

    if message.author.id == status['user_id']:
        try:
            channel = message.channel
            webhook = await get_or_create_webhook(channel)
            
            content = message.content if message.content else None
            
            files = []
            if message.attachments:
                for attachment in message.attachments:
                    try:
                        async with aiohttp.ClientSession() as session:
                            async with session.get(attachment.url) as resp:
                                if resp.status == 200:
                                    file_data = await resp.read()
                                    files.append(discord.File(fp=file_data, filename=attachment.filename))
                    except Exception as e:
                        print(f"Lỗi tải attachment: {e}")
            
            embeds = []
            if message.embeds:
                embeds = message.embeds
            
            await webhook.send(
                content=content,
                username=status['display_name'],
                avatar_url=status['avatar_url'],
                files=files if files else None,
                embeds=embeds if embeds else None
            )
            
        except discord.Forbidden:
            await channel.send("⚠️ Bot không có quyền tạo webhook hoặc gửi tin nhắn!")
        except Exception as e:
            print(f"Lỗi khi gửi tin nhắn fake: {e}")
            try:
                await channel.send(f"⚠️ Lỗi fake message: {str(e)[:100]}")
            except:
                pass

    await bot.process_commands(message)

@bot.tree.command(name="test", description="Kiểm tra bot hoạt động")
async def test(interaction: discord.Interaction):
    embed = discord.Embed(
        title="✅ Bot đang hoạt động!",
        description="Bot đã sẵn sàng để sử dụng",
        color=discord.Color.blue()
    )
    embed.add_field(name="Admin ID", value=f"`{ADMIN_ID}`", inline=False)
    embed.add_field(name="Hướng dẫn", value="Dùng `/fake <user_id>` để bắt đầu fake", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="status", description="Kiểm tra trạng thái fake")
async def status(interaction: discord.Interaction):
    if interaction.user.id != ADMIN_ID:
        await interaction.response.send_message("❌ Bạn không có quyền sử dụng lệnh này!", ephemeral=True)
        return

    if interaction.guild.id in fake_status:
        status_data = fake_status[interaction.guild.id]
        embed = discord.Embed(
            title="📊 Trạng thái fake",
            color=discord.Color.blue()
        )
        embed.add_field(name="User", value=status_data['display_name'], inline=True)
        embed.add_field(name="User ID", value=f"`{status_data['user_id']}`", inline=True)
        embed.add_field(name="Trạng thái", value="✅ Đang hoạt động" if status_data['active'] else "❌ Đã dừng", inline=True)
        embed.set_thumbnail(url=status_data['avatar_url'])
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        await interaction.response.send_message("❌ Chưa có chế độ fake nào được kích hoạt!", ephemeral=True)

if __name__ == "__main__":
    if not TOKEN:
        print("❌ Vui lòng set DISCORD_TOKEN trong environment variables!")
        exit(1)
    bot.run(TOKEN)
