from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    FlexSendMessage, QuickReply, QuickReplyButton, MessageAction
)
import json
import random
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# LINE Bot configuration
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

# ข้อมูล Merchant (ร้านค้า)
merchants = {
    "1": {
        "name": "ร้านป้าเหลือง",
        "logo": "https://s.isanook.com/mn/0/ud/42/211545/mon30087.jpg",
        "opening": "08:00-20:00",
        "rating": 4.5
    },
    "2": {
        "name": "ร้านคอเล่า",
        "logo": "https://static.thairath.co.th/media/dFQROr7oWzulq5Fa5LBgolcgQeMbkDSlIEv1AYhsQFjK9daCrXhTZI38jmHMr0jPlQL.jpg",
        "opening": "10:00-22:00",
        "rating": 4.2
    }
}

# เมนูอาหารแบ่งตาม Merchant
menus = {
    "1": {
        "categories": [
            {
                "name": "อาหารจานเดียว",
                "items": [
                    {"id": "1-1", "name": "ข้าวผัดกระเพราไก่", "price": 45, "image": "https://example.com/padkapow.jpg"},
                    {"id": "1-2", "name": "ข้าวไข่เจียว", "price": 35, "image": "https://example.com/omelette.jpg"}
                ]
            },
            {
                "name": "เครื่องดื่ม",
                "items": [
                    {"id": "1-3", "name": "น้ำเปล่า", "price": 10, "image": "https://example.com/water.jpg"},
                    {"id": "1-4", "name": "น้ำส้ม", "price": 20, "image": "https://example.com/orangejuice.jpg"}
                ]
            }
        ]
    },
    "2": {
        "categories": [
            {
                "name": "ส้มตำ",
                "items": [
                    {"id": "2-1", "name": "ส้มตำไทย", "price": 60, "image": "https://example.com/somtum_thai.jpg"},
                    {"id": "2-2", "name": "ส้มตำปู", "price": 70, "image": "https://example.com/somtum_pu.jpg"}
                ]
            },
            {
                "name": "ของทานเล่น",
                "items": [
                    {"id": "2-3", "name": "ไก่ย่าง", "price": 80, "image": "https://example.com/gaiyang.jpg"},
                    {"id": "2-4", "name": "ลาบหมู", "price": 65, "image": "https://example.com/labmoo.jpg"}
                ]
            }
        ]
    }
}

# เก็บสถานะผู้ใช้
user_sessions = {}

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    user_message = event.message.text.strip()
    
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            "status": "เริ่มต้น",
            "ตะกร้า": [],
            "merchant_id": None
        }
    
    current_session = user_sessions[user_id]
    
    if user_message == 'เลือกร้าน':
        show_merchants(event)
    elif user_message == 'เมนู':
        if current_session["merchant_id"]:
            show_menu(event, current_session["merchant_id"])
        else:
            quick_reply = QuickReply(
                items=[
                    QuickReplyButton(action=MessageAction(label="เลือกร้าน", text="เลือกร้าน")),
                ]
            )

            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="กรุณาเลือกร้านก่อนด้วยคำสั่ง 'เลือกร้าน'", quick_reply=quick_reply),
            )
    elif user_message == 'ดูตะกร้า':
        show_cart(event, current_session)
    elif user_message == 'สั่งอาหาร':
        checkout(event, current_session, user_id)
    elif user_message == 'ยกเลิก':
        cancel_order(event, user_id)
    elif user_message.startswith('เลือกร้าน '):
        merchant_id = user_message.split(' ')[1]
        select_merchant(event, user_id, merchant_id)
    elif user_message.startswith('เพิ่ม '):
        item_id = user_message.split(' ')[1]
        add_to_cart(event, item_id, current_session)
    elif user_message.startswith('ลบ '):
        item_id = user_message.split(' ')[1]
        remove_from_cart(event, item_id, current_session)
    else:
        send_welcome_message(event)

def send_welcome_message(event):
    welcome_text = """🍽️ ข้าวซิ่ง สวัสดีค่ะ
    
คำสั่งที่สามารถใช้ได้:
- พิมพ์ 'เลือกร้าน' เพื่อเลือกร้านค้า
- พิมพ์ 'เมนู' เพื่อดูรายการอาหาร
- พิมพ์ 'ดูตะกร้า' เพื่อตรวจสอบรายการ
- พิมพ์ 'สั่งอาหาร' เพื่อยืนยันการสั่ง
- พิมพ์ 'ยกเลิก' เพื่อยกเลิกการสั่ง

หรือกดปุ่มด้านล่างเพื่อทำรายการค่ะ"""

    quick_reply = QuickReply(
        items=[
            QuickReplyButton(action=MessageAction(label="เลือกร้าน", text="เลือกร้าน")),
            QuickReplyButton(action=MessageAction(label="เมนู", text="เมนู")),
            QuickReplyButton(action=MessageAction(label="ดูตะกร้า", text="ดูตะกร้า")),
            QuickReplyButton(action=MessageAction(label="สั่งอาหาร", text="สั่งอาหาร")),
            QuickReplyButton(action=MessageAction(label="ยกเลิก", text="ยกเลิก")),
        ]
    )
    
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=welcome_text, quick_reply=quick_reply)
    )

def show_merchants(event):
    bubble_contents = []
    
    for merchant_id, merchant in merchants.items():
        bubble = {
            "type": "bubble",
            "hero": {
                "type": "image",
                "url": merchant["logo"],
                "size": "full",
                "aspectRatio": "20:13",
                "aspectMode": "cover"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": merchant["name"],
                        "weight": "bold",
                        "size": "xl"
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "margin": "lg",
                        "spacing": "sm",
                        "contents": [
                            {
                                "type": "box",
                                "layout": "baseline",
                                "spacing": "sm",
                                "contents": [
                                    {
                                        "type": "text",
                                        "text": "เวลาเปิด:",
                                        "color": "#aaaaaa",
                                        "size": "sm",
                                        "flex": 1
                                    },
                                    {
                                        "type": "text",
                                        "text": merchant["opening"],
                                        "wrap": True,
                                        "color": "#666666",
                                        "size": "sm",
                                        "flex": 4
                                    }
                                ]
                            },
                            {
                                "type": "box",
                                "layout": "baseline",
                                "spacing": "sm",
                                "contents": [
                                    {
                                        "type": "text",
                                        "text": "คะแนน:",
                                        "color": "#aaaaaa",
                                        "size": "sm",
                                        "flex": 1
                                    },
                                    {
                                        "type": "text",
                                        "text": str(merchant["rating"]),
                                        "wrap": True,
                                        "color": "#666666",
                                        "size": "sm",
                                        "flex": 4
                                    }
                                ]
                            }
                        ]
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "spacing": "sm",
                "contents": [
                    {
                        "type": "button",
                        "style": "primary",
                        "action": {
                            "type": "message",
                            "label": "เลือกร้านนี้",
                            "text": f"เลือกร้าน {merchant_id}"
                        }
                    }
                ]
            }
        }
        bubble_contents.append(bubble)
    
    flex_message = FlexSendMessage(
        alt_text="เลือกร้านค้า",
        contents={
            "type": "carousel",
            "contents": bubble_contents
        }
    )
    
    line_bot_api.reply_message(
        event.reply_token,
        flex_message
    )

def select_merchant(event, user_id, merchant_id):
    if merchant_id in merchants:
        user_sessions[user_id]["merchant_id"] = merchant_id
        
        merchant = merchants[merchant_id]
        reply_text = f"คุณเลือกร้าน {merchant['name']} แล้ว\nพิมพ์ 'เมนู' เพื่อดูรายการอาหาร"

        quick_reply = QuickReply(
            items=[
                QuickReplyButton(action=MessageAction(label="เมนู", text="เมนู")),
            ]
        )
        
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_text, quick_reply=quick_reply)
        )
    else:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="ไม่พบร้านค้านี้ กรุณาลองใหม่")
        )

def show_menu(event, merchant_id):
    if merchant_id not in menus:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="ไม่พบเมนูของร้านนี้")
        )
        return
    
    menu_data = menus[merchant_id]
    flex_contents = []
    
    for category in menu_data["categories"]:
        # Header for category
        header = {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": category["name"],
                    "weight": "bold",
                    "size": "lg",
                    "color": "#FFFFFF"
                }
            ],
            "backgroundColor": "#FF6B6B",
            "paddingAll": "md",
            "cornerRadius": "md"
        }
        
        # Items in category
        item_boxes = []
        for item in category["items"]:
            item_box = {
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {
                        "type": "image",
                        "url": item["image"],
                        "size": "xxl",
                        "aspectRatio": "1:1",
                        "aspectMode": "cover",
                        "flex": 2
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "flex": 3,
                        "contents": [
                            {
                                "type": "text",
                                "text": item["name"],
                                "weight": "bold",
                                "size": "md"
                            },
                            {
                                "type": "text",
                                "text": f"{item['price']} บาท",
                                "color": "#FF6B6B",
                                "size": "sm"
                            },
                            {
                                "type": "button",
                                "action": {
                                    "type": "message",
                                    "label": "เพิ่มลงตะกร้า",
                                    "text": f"เพิ่ม {item['id']}"
                                },
                                "style": "primary",
                                "height": "sm",
                                "margin": "md"
                            }
                        ],
                        "paddingStart": "md"
                    }
                ],
                "spacing": "md",
                "margin": "md"
            }
            item_boxes.append(item_box)
        
        # Create a bubble for each category
        bubble = {
            "type": "bubble",
            "header": header,
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": item_boxes
            }
        }
        flex_contents.append(bubble)
    
    flex_message = FlexSendMessage(
        alt_text="เมนูอาหาร",
        contents={
            "type": "carousel",
            "contents": flex_contents
        }
    )
    
    line_bot_api.reply_message(
        event.reply_token,
        flex_message
    )

def add_to_cart(event, item_id, session):
    if not session["merchant_id"]:
        quick_reply = QuickReply(
            items=[
                QuickReplyButton(action=MessageAction(label="เลือกร้าน", text="เลือกร้าน")),
            ]
        )

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="กรุณาเลือกร้านก่อน", quick_reply=quick_reply)
        )
        return
    
    # Find item in menu
    item_found = None
    for category in menus[session["merchant_id"]]["categories"]:
        for item in category["items"]:
            if item["id"] == item_id:
                item_found = item
                break
        if item_found:
            break
    
    if item_found:
        session["ตะกร้า"].append(item_found)
        reply_text = f"เพิ่ม {item_found['name']} ลงตะกร้าเรียบร้อย\nพิมพ์ 'ดูตะกร้า' เพื่อตรวจสอบ"

        quick_reply = QuickReply(
            items=[
                QuickReplyButton(action=MessageAction(label="ดูตะกร้า", text="ดูตะกร้า")),
            ]
        )
        
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_text, quick_reply=quick_reply)
        )
    else:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="ไม่พบรายการอาหารนี้")
        )

def show_cart(event, session):
    if not session["ตะกร้า"]:
        quick_reply = QuickReply(
            items=[
                QuickReplyButton(action=MessageAction(label="เลือกร้าน", text="เลือกร้าน")),
                QuickReplyButton(action=MessageAction(label="ยกเลิก", text="ยกเลิก")),
            ]
        )

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="ตะกร้าว่างเปล่า", quick_reply=quick_reply)
        )
        return
    
    merchant = merchants[session["merchant_id"]]
    total = sum(item["price"] for item in session["ตะกร้า"])
    
    # Create order summary
    order_items = []
    for item in session["ตะกร้า"]:
        order_items.append({
            "type": "box",
            "layout": "horizontal",
            "contents": [
                {
                    "type": "text",
                    "text": item["name"],
                    "flex": 3,
                    "size": "sm"
                },
                {
                    "type": "text",
                    "text": f"{item['price']} บาท",
                    "flex": 1,
                    "size": "sm",
                    "align": "end"
                }
            ]
        })
    
    flex_message = FlexSendMessage(
        alt_text="ตะกร้าสินค้า",
        contents={
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "ตะกร้าสินค้า",
                        "weight": "bold",
                        "size": "xl"
                    },
                    {
                        "type": "text",
                        "text": merchant["name"],
                        "color": "#666666",
                        "size": "sm"
                    }
                ]
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": order_items + [
                    {
                        "type": "separator",
                        "margin": "md"
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "margin": "md",
                        "contents": [
                            {
                                "type": "text",
                                "text": "รวมทั้งหมด",
                                "weight": "bold",
                                "size": "md"
                            },
                            {
                                "type": "text",
                                "text": f"{total} บาท",
                                "weight": "bold",
                                "size": "md",
                                "align": "end"
                            }
                        ]
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "button",
                        "action": {
                            "type": "message",
                            "label": "สั่งอาหาร",
                            "text": "สั่งอาหาร"
                        },
                        "style": "primary"
                    },
                    {
                        "type": "button",
                        "action": {
                            "type": "message",
                            "label": "ยกเลิกการสั่ง",
                            "text": "ยกเลิก"
                        },
                        "margin": "md",
                        "style": "secondary"
                    }
                ]
            }
        }
    )
    
    line_bot_api.reply_message(
        event.reply_token,
        flex_message
    )

def remove_from_cart(event, item_number, session):
    try:
        index = int(item_number) - 1
        if 0 <= index < len(session["ตะกร้า"]):
            removed_item = session["ตะกร้า"].pop(index)
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"ยกเลิก {removed_item['name']} จากตะกร้าเรียบร้อย")
            )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="ไม่มีรายการนี้ในตะกร้าค่ะ")
            )
    except ValueError:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="กรุณาพิมพ์เลขเมนูที่ต้องการลบ เช่น 'ลบ 1'")
        )

def checkout(event, session, user_id):
    if not session["ตะกร้า"]:
        quick_reply = QuickReply(
            items=[
                QuickReplyButton(action=MessageAction(label="เลือกร้าน", text="เลือกร้าน")),
                QuickReplyButton(action=MessageAction(label="ยกเลิก", text="ยกเลิก")),
            ]
        )

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="ตะกร้าว่างเปล่า", quick_reply=quick_reply)
        )
        return
    
    merchant = merchants[session["merchant_id"]]
    total = sum(item["price"] for item in session["ตะกร้า"])
    order_number = random.randint(1000, 9999)
    order_time = datetime.now().strftime("%H:%M")
    
    # Create order confirmation
    order_items = []
    for item in session["ตะกร้า"]:
        order_items.append({
            "type": "box",
            "layout": "horizontal",
            "contents": [
                {
                    "type": "text",
                    "text": item["name"],
                    "flex": 3,
                    "size": "sm"
                },
                {
                    "type": "text",
                    "text": f"{item['price']} บาท",
                    "flex": 1,
                    "size": "sm",
                    "align": "end"
                }
            ]
        })
    
    flex_message = FlexSendMessage(
        alt_text="ยืนยันการสั่งอาหาร",
        contents={
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "✅ สั่งอาหารสำเร็จ",
                        "weight": "bold",
                        "size": "xl",
                        "color": "#00C300"
                    },
                    {
                        "type": "text",
                        "text": f"เลขที่คำสั่ง: #{order_number}",
                        "margin": "sm"
                    },
                    {
                        "type": "text",
                        "text": f"เวลา: {order_time}",
                        "margin": "sm"
                    }
                ]
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": merchant["name"],
                        "weight": "bold",
                        "margin": "md"
                    },
                    {
                        "type": "separator",
                        "margin": "md"
                    }
                ] + order_items + [
                    {
                        "type": "separator",
                        "margin": "md"
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "margin": "md",
                        "contents": [
                            {
                                "type": "text",
                                "text": "รวมทั้งหมด",
                                "weight": "bold",
                                "size": "md"
                            },
                            {
                                "type": "text",
                                "text": f"{total} บาท",
                                "weight": "bold",
                                "size": "md",
                                "align": "end"
                            }
                        ]
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "อาหารจะจัดส่งภายใน 30 นาที",
                        "align": "center",
                        "margin": "md",
                        "color": "#666666"
                    },
                    {
                        "type": "button",
                        "action": {
                            "type": "uri",
                            "label": "ติดตามออเดอร์",
                            "uri": "https://example.com/track"
                        },
                        "margin": "md"
                    }
                ]
            }
        }
    )
    
    line_bot_api.reply_message(
        event.reply_token,
        flex_message
    )
    
    # Reset cart
    session["ตะกร้า"] = []

def cancel_order(event, user_id):
    if user_id in user_sessions:
        user_sessions[user_id]["ตะกร้า"] = []
    
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="ยกเลิกการสั่งอาหารเรียบร้อยแล้ว")
    )

if __name__ == "__main__":
    app.run(port=5000)