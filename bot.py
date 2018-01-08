import os
import telegram
import secrets
import logging
import re

from telegram import Bot, Update
from telegram.ext import Updater, CommandHandler
from typing import List

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

with open('token.txt') as f:
    BOT_TOKEN = f.read()

DICE_TYPE_PATTERN = re.compile('^d(\d+)')
DICE_ROLL_PATTERN = re.compile('^(\d+)d(\d+)$')
FATE_ROLL_PATTERN = re.compile('^(\d+)d$')

MAX_FACE = 1000
MAX_NUM = 200
WEB_HOOK = False


class UnsupportedDice(Exception):
    pass


class Dice:
    DEFAULT_NUM = 1

    def __init__(self, face_num: int):
        self.face = face_num

    def roll(self) -> int:
        return secrets.randbelow(self.face) + 1

    def roll_n(self, dice_num) -> [int]:
        return [self.roll() for _ in range(dice_num)]

    def display(self, roll_result: [int]):
        result = ", ".join(["{:2}".format(r) for r in roll_result])
        num = len(roll_result)
        if num == 1:
            return "`1d{}` 🎲 `{}`".format(self.face, result)
        else:
            return "{}d{}` 🎲 `{}`\nsum: `{}` max: `{}` min: `{}`".format(
                num, self.face, result, sum(roll_result), max(roll_result), min(roll_result))


class FateDice(Dice):
    DEFAULT_NUM = 4

    def __init__(self):
        super(FateDice, self).__init__(6)

    def roll(self):
        result = super(FateDice, self).roll()
        if result > 4:
            return 1
        elif result < 3:
            return -1
        else:
            return 0

    def display(self, roll_result: [int]):
        def to_str(x: int):
            if x == 0:
                return '⬜️️'
            elif x > 0:
                return '➕'
            elif x < 0:
                return '➖'
        result = " ".join([to_str(r) for r in roll_result])
        return "{}×FATE {} sum: `{}`".format(len(roll_result), result, sum(roll_result))


def db_and_build(str_: int, siz: int) -> (str, int):
    a = str_ + siz
    if a < 65:
        return '-2', -2
    elif a < 85:
        return '-1', -1
    elif a < 125:
        return '0', 0
    elif a < 165:
        return '+1d4', 1
    elif a < 205:
        return '+1d6', 2
    elif a < 285:
        return '+2d6', 3
    elif a < 365:
        return '+3d6', 4
    elif a < 445:
        return '+4d6', 5
    else:
        return '+5d6', 6


def coc7stats(bot: Bot, update: Update, args: List[str]):
    chat_id = update.message.chat_id

    if len(args) != 1 or not args[0].isnumeric():
        bot.send_message(chat_id,
                         "召唤方式错误哦，只需要跟一个年龄参数，像这样 `/coc7stats 18` 。",
                         parse_mode='Markdown')
        return
    age = int(args[0])
    d6 = Dice(6)
    d10 = Dice(10)
    d100 = Dice(100)
    str_ = sum(d6.roll_n(3)) * 5
    con = sum(d6.roll_n(3)) * 5
    dex = sum(d6.roll_n(3)) * 5
    pow_ = sum(d6.roll_n(3)) * 5
    app = sum(d6.roll_n(3)) * 5
    luck = sum(d6.roll_n(3)) * 5
    luck2 = sum(d6.roll_n(3)) * 5
    siz = sum(d6.roll_n(2), 6) * 5
    int_ = sum(d6.roll_n(2), 6) * 5
    edu = sum(d6.roll_n(2), 6) * 5
    mov = 8
    if dex < siz and str_ < siz:
        mov = 7
    elif dex > siz and str_ > siz:
        mov = 9

    def edu_enhance(e: int):
        if d100.roll() > e:
            e += d10.roll()
        return min(99, e)

    warning = ""
    if age < 15:
        warning = "小于十五岁的调查员需要咨询KP调整属性值"
    elif age < 20:
        warning = "请将力量和体型合计减 5 点。"
        luck = max(luck, luck2)
    elif age < 40:
        edu = edu_enhance(edu)
    elif age < 50:
        warning = "请将力量、敏捷和体质合计减 5 点。"
        app -= 5
        mov -= 1
        edu = edu_enhance(edu)
        edu = edu_enhance(edu)
    elif age < 60:
        warning = "请将力量、敏捷和体质合计减 10 点。"
        app -= 10
        mov -= 2
        edu = edu_enhance(edu)
        edu = edu_enhance(edu)
        edu = edu_enhance(edu)
    elif age < 70:
        warning = "请将力量、敏捷和体质合计减 20 点。"
        app -= 15
        mov -= 3
        edu = edu_enhance(edu)
        edu = edu_enhance(edu)
        edu = edu_enhance(edu)
        edu = edu_enhance(edu)
    elif age < 80:
        warning = "请将力量、敏捷和体质合计减 40 点。"
        app -= 20
        mov -= 4
        edu = edu_enhance(edu)
        edu = edu_enhance(edu)
        edu = edu_enhance(edu)
        edu = edu_enhance(edu)
    elif age <= 90:
        warning = "请将力量、敏捷和体质合计减 80 点。"
        app -= 25
        mov -= 5
        edu = edu_enhance(edu)
        edu = edu_enhance(edu)
        edu = edu_enhance(edu)
        edu = edu_enhance(edu)
    else:
        warning = "大于九十岁的调查员请询问KP"

    db, build = db_and_build(str_, siz)

    stats = '''
```
力量  STR: {str:2}  
体质  CON: {con:2}
体形  SIZ: {siz:2}  
敏捷  DEX: {dex:2}
外表  APP: {app:2}
教育  EDU: {edu:2}
智力  INT: {int:2}
意志  POW: {pow:2}
幸运 Luck: {luck:2}

体力 HP: {hp:2}
理智 SAN: {pow:2}
魔法 MP: {mp:2}
移动力 MOV: {mov:2}
体格 Build: {build:2}
伤害加值 DB: {db:2}
```

已根据年龄调整了教育、移动力以及幸运。
{0}
    '''.format(warning, str=str_, dex=dex, int=int_, con=con, app=app, pow=pow_,
               siz=siz, edu=edu, mov=mov, luck=luck, hp=(siz+con)//10, mp=pow_//5,
               build=build, db=db)
    bot.send_message(chat_id, stats, parse_mode='Markdown')


def set_default_dice(bot: Bot, update: Update, args: [str], chat_data: dict):
    chat_id = update.message.chat_id
    if len(args) != 1:
        bot.send_message(
            chat_id,
            "诶呀，召唤我的方式出错了! `/set_default_dice` 后面跟一个形如 `d100` 的哦",
            parse_mode='Markdown')
        return

    arg = args[0]
    normal = DICE_TYPE_PATTERN.match(arg)
    if normal is not None:
        face_num = int(normal.group(1))
        if face_num > MAX_FACE:
            bot.send_message(chat_id, "骰子的面数太多了，你在想什么！")
        chat_data['dice'] = Dice(face_num)
        bot.send_message(chat_id, "已设定当前默认骰子为{}面骰".format(face_num))
    elif arg == 'fate':
        chat_data['dice'] = FateDice()
        bot.send_message(chat_id, "已设定当前默认骰子为FATE骰子")
    else:
        bot.send_message(chat_id, "这种类型的骰子没办法设为默认骰子")


def command_roll(bot: Bot, update: Update, args: [str], chat_data: dict):
    msg = update.message
    dice = Dice(face_num=100)
    if 'dice' in chat_data:
        dice = chat_data['dice']

    dice_num = dice.DEFAULT_NUM

    if len(args) == 1:
        roll_cmd = DICE_ROLL_PATTERN.match(args[0])
        if roll_cmd is not None:
            dice_num = int(roll_cmd.group(1))
            dice = Dice(int(roll_cmd.group(2)))
        else:
            bot.send_message(msg.chat_id, "抱歉，指令错误")
            return
    if dice_num > MAX_NUM:
        bot.send_message(msg.chat_id, "找不到那么多骰子啦～")
        return
    results = dice.roll_n(dice_num)

    bot.send_message(msg.chat_id, dice.display(results),
                     reply_to_message_id=msg.message_id, parse_mode='Markdown')


def main():
    updater = Updater(token=BOT_TOKEN)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler('r', command_roll, pass_args=True, pass_chat_data=True))
    dispatcher.add_handler(CommandHandler('coc7stats', coc7stats, pass_args=True))
    dispatcher.add_handler(
        CommandHandler('set_default_dice', set_default_dice, pass_args=True, pass_chat_data=True))
    if WEB_HOOK:
        # TODO: work in processing.
        updater.start_webhook(listen='127.0.0.1', port=5000, url_path=BOT_TOKEN)
    else:
        updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
