import sys
import types
import asyncio
import aiohttp
import os
from dotenv import load_dotenv

# Tạo mock audioop TRƯỚC KHI import discord
class MockAudioop:
    def __getattr__(self, name):
        return lambda *args, **kwargs: b''

sys.modules['audioop'] = MockAudioop()

import discord
from discord.ext import commands

load_dotenv()

# Lấy token từ env
TOKENS = [
    os.getenv('DISCORD_TOKEN_1'),
    os.getenv('DISCORD_TOKEN_2'),
    os.getenv('DISCORD_TOKEN_3')
]

ADMIN_ID = 1512658477841908015

# Lưu trạng thái fake cho từng token
bot_instances = []

class FakeBot:
    def __init__(self, token, bot_id):
        self.token = token
        self.bot_id = bot_id
        self.bot = None
        self.fake_status = {
            'user_id': None,
            'display_name': None,
            'avatar_url': None,
            'active': False
        }
        # Lưu tin nhắn đã fake để edit
        self.fake_messages = {}  # {message_id: fake_message_id}
        self.setup_bot()

    def setup_bot(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True

        self.bot = commands.Bot(command_prefix='/', intents=intents)

        @self.bot.event
        async def on_ready():
            print(f'✅ Bot {self.bot_id} đã sẵn sàng! Logged in as {self.bot.user} (ID: {self.bot.user.id})')
            try:
                synced = await self.bot.tree.sync()
                print(f"✅ Bot {self.bot_id} đã sync {len(synced)} lệnh slash")
            except Exception as e:
                print(f"❌ Bot {self.bot_id} lỗi sync: {e}")

        @self.bot.tree.command(name=f"fake{self.bot_id}", description=f"Fake user với bot {self.bot_id} (Chỉ admin)")
        async def fake(interaction: discord.Interaction, user_id: str):
            if interaction.user.id != ADMIN_ID:
                await interaction.response.send_message("❌ Bạn không có quyền!", ephemeral=True)
                return

            try:
                user_id_int = int(user_id)
            except ValueError:
                await interaction.response.send_message("❌ ID không hợp lệ!", ephemeral=True)
                return

            target_user = interaction.guild.get_member(user_id_int)
            if not target_user:
                await interaction.response.send_message("❌ Không tìm thấy user!", ephemeral=True)
                return

            try:
                avatar_url = target_user.display_avatar.url
                display_name = target_user.display_name
                
                # Tải avatar
                async with aiohttp.ClientSession() as session:
                    async with session.get(avatar_url) as resp:
                        if resp.status == 200:
                            avatar_data = await resp.read()
                        else:
                            await interaction.response.send_message("❌ Không thể tải avatar!", ephemeral=True)
                            return
            except Exception as e:
                await interaction.response.send_message(f"❌ Lỗi: {str(e)[:100]}", ephemeral=True)
                return

            # Lưu thông tin
            self.fake_status = {
                'user_id': user_id_int,
                'display_name': display_name,
                'avatar_url': avatar_url,
                'active': True
            }

            # Đổi tên và avatar
            try:
                await self.bot.user.edit(username=display_name[:32])
                await self.bot.user.edit(avatar=avatar_data)
                
                embed = discord.Embed(
                    title=f"✅ Bot {self.bot_id} đã fake!",
                    description=f"Đang fake: **{display_name}**",
                    color=discord.Color.green()
                )
                embed.set_thumbnail(url=avatar_url)
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except Exception as e:
                await interaction.response.send_message(f"❌ Lỗi đổi tên: {str(e)[:100]}", ephemeral=True)

        @self.bot.tree.command(name=f"stop_fake{self.bot_id}", description=f"Dừng fake bot {self.bot_id}")
        async def stop_fake(interaction: discord.Interaction):
            if interaction.user.id != ADMIN_ID:
                await interaction.response.send_message("❌ Không có quyền!", ephemeral=True)
                return

            self.fake_status['active'] = False
            self.fake_messages.clear()
            await interaction.response.send_message(f"✅ Bot {self.bot_id} đã dừng fake!", ephemeral=True)

        @self.bot.tree.command(name=f"reset{self.bot_id}", description=f"Reset bot {self.bot_id} về mặc định")
        async def reset(interaction: discord.Interaction):
            if interaction.user.id != ADMIN_ID:
                await interaction.response.send_message("❌ Không có quyền!", ephemeral=True)
                return

            try:
                await self.bot.user.edit(username=f"Fake Bot {self.bot_id}")
                await self.bot.user.edit(avatar=None)
                self.fake_status['active'] = False
                self.fake_messages.clear()
                await interaction.response.send_message(f"✅ Bot {self.bot_id} đã reset!", ephemeral=True)
            except Exception as e:
                await interaction.response.send_message(f"❌ Lỗi reset: {str(e)[:100]}", ephemeral=True)

        @self.bot.tree.command(name=f"status{self.bot_id}", description=f"Trạng thái bot {self.bot_id}")
        async def status_cmd(interaction: discord.Interaction):
            if interaction.user.id != ADMIN_ID:
                await interaction.response.send_message("❌ Không có quyền!", ephemeral=True)
                return

            if self.fake_status['active']:
                embed = discord.Embed(
                    title=f"📊 Bot {self.bot_id}",
                    color=discord.Color.blue()
                )
                embed.add_field(name="User", value=self.fake_status['display_name'], inline=True)
                embed.add_field(name="Status", value="✅ Đang fake", inline=True)
                embed.add_field(name="Tin nhắn đã fake", value=len(self.fake_messages), inline=True)
                embed.set_thumbnail(url=self.fake_status['avatar_url'])
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ Bot {self.bot_id} đang ở chế độ mặc định!", ephemeral=True)

        @self.bot.event
        async def on_message(message):
            if message.author.bot:
                return

            if not message.guild:
                return

            if not self.fake_status['active']:
                await self.bot.process_commands(message)
                return

            # Nếu tin nhắn từ user đang bị fake
            if message.author.id == self.fake_status['user_id']:
                try:
                    channel = message.channel
                    content = message.content if message.content else ""
                    
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
                                print(f"Lỗi tải attachment bot {self.bot_id}: {e}")
                    
                    # Gửi tin nhắn và lưu ID
                    if files:
                        sent_msg = await channel.send(content=content, files=files)
                    else:
                        if content:
                            sent_msg = await channel.send(content=content)
                        elif message.embeds:
                            for embed in message.embeds:
                                sent_msg = await channel.send(embed=embed)
                        else:
                            sent_msg = None
                    
                    # Lưu ID tin nhắn gốc và tin nhắn đã fake
                    if sent_msg:
                        self.fake_messages[message.id] = sent_msg.id
                            
                except Exception as e:
                    print(f"Lỗi gửi tin nhắn bot {self.bot_id}: {e}")

            await self.bot.process_commands(message)

        @self.bot.event
        async def on_message_edit(before, after):
            """Xử lý khi user sửa tin nhắn"""
            if before.author.bot:
                return

            if not before.guild:
                return

            if not self.fake_status['active']:
                return

            # Nếu tin nhắn được sửa từ user đang bị fake
            if before.author.id == self.fake_status['user_id']:
                try:
                    # Tìm tin nhắn đã fake tương ứng
                    if before.id in self.fake_messages:
                        fake_msg_id = self.fake_messages[before.id]
                        channel = before.channel
                        
                        # Lấy tin nhắn đã fake
                        try:
                            fake_msg = await channel.fetch_message(fake_msg_id)
                            
                            # Cập nhật nội dung mới
                            new_content = after.content if after.content else ""
                            
                            # Xử lý attachments mới
                            files = []
                            if after.attachments:
                                for attachment in after.attachments:
                                    try:
                                        async with aiohttp.ClientSession() as session:
                                            async with session.get(attachment.url) as resp:
                                                if resp.status == 200:
                                                    file_data = await resp.read()
                                                    files.append(discord.File(fp=file_data, filename=attachment.filename))
                                    except Exception as e:
                                        print(f"Lỗi tải attachment bot {self.bot_id}: {e}")
                            
                            # Sửa tin nhắn đã fake
                            if files:
                                await fake_msg.edit(content=new_content, attachments=files)
                            else:
                                if new_content:
                                    await fake_msg.edit(content=new_content)
                                elif after.embeds:
                                    await fake_msg.edit(embeds=after.embeds)
                                else:
                                    await fake_msg.edit(content="")
                                    
                            print(f"✅ Bot {self.bot_id} đã sửa tin nhắn fake (ID: {fake_msg_id})")
                            
                        except discord.NotFound:
                            # Tin nhắn đã bị xóa, xóa khỏi cache
                            del self.fake_messages[before.id]
                        except Exception as e:
                            print(f"Lỗi sửa tin nhắn bot {self.bot_id}: {e}")
                            
                except Exception as e:
                    print(f"Lỗi xử lý sửa tin nhắn bot {self.bot_id}: {e}")

        @self.bot.event
        async def on_message_delete(message):
            """Xử lý khi user xóa tin nhắn"""
            if message.author.bot:
                return

            if not message.guild:
                return

            if not self.fake_status['active']:
                return

            # Nếu tin nhắn bị xóa từ user đang bị fake
            if message.author.id == self.fake_status['user_id']:
                try:
                    # Tìm tin nhắn đã fake tương ứng
                    if message.id in self.fake_messages:
                        fake_msg_id = self.fake_messages[message.id]
                        channel = message.channel
                        
                        # Xóa tin nhắn đã fake
                        try:
                            fake_msg = await channel.fetch_message(fake_msg_id)
                            await fake_msg.delete()
                            del self.fake_messages[message.id]
                            print(f"✅ Bot {self.bot_id} đã xóa tin nhắn fake (ID: {fake_msg_id})")
                        except discord.NotFound:
                            del self.fake_messages[message.id]
                        except Exception as e:
                            print(f"Lỗi xóa tin nhắn bot {self.bot_id}: {e}")
                            
                except Exception as e:
                    print(f"Lỗi xử lý xóa tin nhắn bot {self.bot_id}: {e}")

    async def start(self):
        await self.bot.start(self.token)

async def main():
    # Tạo và chạy các bot
    tasks = []
    for i, token in enumerate(TOKENS, 1):
        if token:
            bot_instance = FakeBot(token, i)
            bot_instances.append(bot_instance)
            tasks.append(bot_instance.start())
            print(f"🚀 Đang khởi động Bot {i}...")
        else:
            print(f"⚠️ Bot {i} không có token!")

    # Chạy tất cả bot cùng lúc
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    # Kiểm tra token
    active_tokens = [t for t in TOKENS if t]
    if not active_tokens:
        print("❌ Không có token nào! Vui lòng set DISCORD_TOKEN_1, DISCORD_TOKEN_2, DISCORD_TOKEN_3 trong .env")
        exit(1)
    
    print(f"🚀 Khởi động {len(active_tokens)} bot...")
    asyncio.run(main())
