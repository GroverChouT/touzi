import os
import telegram
import secrets
import logging
import re

from telegram import Bot, Update, ReplyKeyboardRemove, Chat
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler
from bot_token import BOT_TOKEN

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

DICE_TYPE_PATTERN = re.compile('^d(\d+)')
DICE_ROLL_PATTERN = re.compile('^(\d+)d(\d+)$')
MAX_FACE = 1000
MAX_NUM = 200

def dice(face_num: int):
    return secrets.randbelow(face_num) + 1


def set_default_dice(bot: Bot, update: Update, args: [str], chat_data: dict):
    text = "诶呀，召唤我的方式出错了! `/set_default_dice` 后面跟一个 `d100` 或 `d20` 或 `d6` 哦"
    if len(args) != 1:
        bot.send_message(update.message.chat_id, text, parse_mode='Markdown')
        return

    arg = DICE_TYPE_PATTERN.match(args[0])
    if arg is not None:
        face_num = int(arg.group(1))
        if face_num <= MAX_FACE:
            chat_data['dice_type'] = 'normal'
            chat_data['dice_face'] = face_num
            bot.send_message(update.message.chat_id, "已设定默认骰子为{}面骰".format(face_num))
            return

    bot.send_message(update.message.chat_id, "暂时不支持这种类型的骰子设为默认骰子")



def roll(bot: Bot, update: Update, args: [str], chat_data: dict):
    dice_num = 1
    dice_face = 100
    if 'dice_type' in chat_data and chat_data['dice_type'] == 'normal':
        dice_face = chat_data['dice_face']
    if len(args) == 1:
        roll_cmd = DICE_ROLL_PATTERN.match(args[0])
        if roll_cmd is not None:
            dice_num = int(roll_cmd.group(1))
            dice_face = int(roll_cmd.group(2))
        else:
            bot.send_message(update.message.chat_id, "抱歉，指令错误")
            return
    if dice_num > MAX_NUM:
        bot.send_message(update.message.chat_id, "找不到那么多骰子啦～～～")
        return
    results = [dice(dice_face) for _ in range(dice_num)]
    if dice_num == 1:
        text = "`{}d{}` 🎲 `{}`".format(dice_num, dice_face, results[0])
    else:
        text = "`{}d{}` 🎲 `{}`\nsum: `{}` max: `{}` min: `{}`"\
            .format(dice_num, dice_face, repr(results), sum(results), max(results), min(results))
    bot.send_message(update.message.chat_id, text, reply_to_message_id=update.message.message_id, parse_mode='Markdown')


def main():
    updater = Updater(token=BOT_TOKEN)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler('r', roll, pass_args=True, pass_chat_data=True))
    dispatcher.add_handler(CommandHandler('set_default_dice', set_default_dice, pass_args=True, pass_chat_data=True))
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
