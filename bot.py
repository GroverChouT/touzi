import os
import re
import secrets
from typing import List

from telegram import Bot, Update
from telegram.ext import Updater, CommandHandler

MAX_FACE = 1000
MAX_NUM = 200


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


def db_and_build(stats: dict):
    a = stats['str'] + stats['size']
    if a < 65:
        db, build = '-2', -2
    elif a < 85:
        db, build = '-1', -1
    elif a < 125:
        db, build = '0', 0
    elif a < 165:
        db, build = '+1d4', 1
    elif a < 205:
        db, build = '+1d6', 2
    elif a < 285:
        db, build = '+2d6', 3
    elif a < 365:
        db, build = '+3d6', 4
    elif a < 445:
        db, build = '+4d6', 5
    else:
        db, build = '+5d6', 6
    stats['db'] = db
    stats['build'] = build


def coc7stats(bot: Bot, update: Update, args: List[str]):
    chat_id = update.message.chat_id
    age = int(args[0])
    if len(args) != 1 or not args[0].isnumeric():
        bot.send_message(chat_id,
                         "召唤方式错误哦，只需要跟一个年龄参数，像这样 `/coc7 18` 。",
                         parse_mode='Markdown')
        return

    d6 = Dice(6)
    d10 = Dice(10)
    d100 = Dice(100)

    stats = {
        "age": int(args[0]),
        "str": sum(d6.roll_n(3)) * 5,
        "con": sum(d6.roll_n(3)) * 5,
        "dex": sum(d6.roll_n(3)) * 5,
        "pow_": sum(d6.roll_n(3)) * 5,
        "app": sum(d6.roll_n(3)) * 5,
        "luck": sum(d6.roll_n(3)) * 5,
        "luck2": sum(d6.roll_n(3)) * 5,
        "size": sum(d6.roll_n(2), 6) * 5,
        "int": sum(d6.roll_n(2), 6) * 5,
        "edu": sum(d6.roll_n(2), 6) * 5,
        "mov": 8,
    }

    if stats['dex'] < stats['size'] and stats['str'] < stats['size']:
        stats['mov'] = 7
    elif stats['dex'] > stats['size'] and stats['str'] > stats['size']:
        stats['mov'] = 9

    def edu_enhance(time: int, edu: int):
        track = []
        for _ in range(time):
            if d100.roll() > edu:
                delta = d10.roll()
                edu += delta
                track.append(delta)
        return min(99, edu)

    warning = ""
    if age < 15:
        warning = "小于十五岁的调查员需要咨询KP调整属性值"
    elif age < 20:
        warning = "请将力量和体型合计减 5 点。\n\n幸运已投掷两次取了大值（可放弃） {} {}" \
            .format(stats['luck'], stats['luck2'])
        stats['luck'] = max(stats['luck'], stats['luck2'])
    elif age < 40:
        stats['edu'] = edu_enhance(1, stats['edu'])
    elif age < 50:
        warning = "请将力量、敏捷和体质合计减 5 点。"
        stats['app'] -= 5
        stats['mov'] -= 1
        stats['edu'] = edu_enhance(2, stats['edu'])
    elif age < 60:
        warning = "请将力量、敏捷和体质合计减 10 点。"
        stats['app'] -= 10
        stats['mov'] -= 2
        stats['edu'] = edu_enhance(3, stats['edu'])
    elif age < 70:
        warning = "请将力量、敏捷和体质合计减 20 点。"
        stats['app'] -= 15
        stats['mov'] -= 3
        stats['edu'] = edu_enhance(4, stats['edu'])
    elif age < 80:
        warning = "请将力量、敏捷和体质合计减 40 点。"
        stats['app'] -= 20
        stats['mov'] -= 4
        stats['edu'] = edu_enhance(4, stats['edu'])
    elif age <= 90:
        warning = "请将力量、敏捷和体质合计减 80 点。"
        stats['app'] -= 25
        stats['mov'] -= 5
        stats['edu'] = edu_enhance(4, stats['edu'])
    else:
        warning = "大于九十岁的调查员请询问KP"

    db_and_build(stats)
    stats['hp'] = (stats['size'] + stats['con']) // 10
    stats['mp'] = stats['pow'] // 5
    stats_text = '''
```
力量  STR: {str:2}  
体质  CON: {con:2}
体形  SIZ: {size:2}  
敏捷  DEX: {dex:2}
外表  APP: {app:2}
教育  EDU: {edu:2}
智力  INT: {int:2}
意志  POW: {pow:2}
幸运 Luck: {luck:2}

体力  HP: {hp:2}
理智 SAN: {pow:2}
魔法  MP: {mp:2}
移动力 MOV: {mov:2}
体格 Build: {build:2}
伤害加值 DB: {db:2}
```

已根据年龄调整了教育、移动力以及幸运。
{0}
    '''.format(warning, **stats)
    bot.send_message(chat_id, stats_text, parse_mode='Markdown')
    return


DICE_TYPE_PATTERN = re.compile('^d(\d+)')


def set_default_dice(bot: Bot, update: Update, args: [str], chat_data: dict):
    chat_id = update.message.chat_id

    # 没有参数
    if len(args) != 1:
        bot.send_message(
            chat_id,
            "诶呀，召唤我的方式出错了! `/set_dice` 后面跟一个形如 `d100` 的哦",
            parse_mode='Markdown'
        )
        return

    arg = args[0]
    normal = DICE_TYPE_PATTERN.match(arg)
    if normal is not None:
        face_num = int(normal.group(1))
        if face_num > MAX_FACE:
            bot.send_message(chat_id, "骰子的面数太多了，你在想什么！")
        chat_data['dice'] = Dice(face_num)
        bot.send_message(chat_id, "已设定当前默认骰子为{}面骰".format(face_num))
    else:
        bot.send_message(chat_id, "这种类型的骰子没办法设为默认骰子")


DICE_ROLL_PATTERN = re.compile('^(\d+)d(\d+)$')


def command_roll(bot: Bot, update: Update, args: [str], chat_data: dict):
    msg = update.message

    # 默认的骰子面数
    dice = Dice(face_num=100)
    if 'dice' in chat_data:
        dice = chat_data['dice']

    # 默认的骰子个数
    dice_num = dice.DEFAULT_NUM

    if len(args) > 1:
        bot.send_message(msg.chat_id, "暂时不支持复杂的指令")
        return

    # 显式指定的命令
    elif len(args) == 1:
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
    updater = Updater(token=os.environ['BOT_TOKEN'])
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler('r', command_roll, pass_args=True, pass_chat_data=True))
    dispatcher.add_handler(CommandHandler('coc7', coc7stats, pass_args=True))
    dispatcher.add_handler(
        CommandHandler('setdice', set_default_dice, pass_args=True, pass_chat_data=True))
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
