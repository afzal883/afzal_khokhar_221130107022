import json,os,random,string
import jwt
import threading
import sys
import os
import logging

from datetime import datetime
from decouple import Config, RepositoryEnv, config
from django.core.mail import send_mail
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden
from django.core.mail import EmailMultiAlternatives
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.shortcuts import render
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.decorators import api_view , permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from playwright.sync_api import sync_playwright

from accounts.models import *
from mainapp.serializers import *
from mainapp.models import *
from celery import shared_task

User = get_user_model()
try:
    config = Config(RepositoryEnv('/var/www/icon_perfumes/backend/.env'))
except:
    pass

logger = logging.getLogger('error_log')

log_file = config('ERROR_LOG_FILE')
EXUCUTABLE_PATH_CHROMIUM=config('EXUCUTABLE_PATH_CHROMIUM')
if not settings.DEBUG:
    sys.stderr = open(log_file, 'a')

BASE_URL  = config('BASE_URL')
WEB_URL = config('WEB_URL')
WEB_URL_FOR_IMAGES = config('WEB_URL_FOR_IMAGES')
ADMIN_EMAIL = config('ADMIN_EMAIL')
current_year = datetime.now().year
SELLER_LOCATION_ID = config('SELLER_LOCATION_ID')  
SHIPPING_CUSTOMER_NAME = config('SHIPPING_CUSTOMER_NAME')
SHIPPING_ADDRESS = config('SHIPPING_ADDRESS')
SHIPPING_CITY = config('SHIPPING_CITY')
SHIPPING_STATE = config('SHIPPING_STATE')
SHIPPING_COUNTRY = config('SHIPPING_COUNTRY')
SHIPPING_PINCODE = config('SHIPPING_PINCODE')
SHIPPING_PHONE = config('SHIPPING_PHONE')

RAZORPAY_KEY_ID = config('RAZORPAY_KEY_ID')
RAZORPAY_SECRET_KEY = config('RAZORPAY_SECRET_KEY')

def save_order_in_thread(order,email, timestamp):
    # Use threading to save the order in a synchronous manner
    def save_order():
        try:
            # Saving PDF file path to the order object
            order.invoice = f'invoices/invoice_{order.id}_{timestamp}.pdf'
            order.save()  # Save the order synchronously
            if not settings.DEBUG:
                send_confirmation_email(email, order)
        except Exception as e:
            print(f"Error saving order: {e}")

    # Start a new thread to execute the save operation
    
    threading.Thread(target=save_order).start()

def send_confirmation_email(user_email,order):

    # Convert individual order items
    logger.info("inside send confirmation")
    converted_items = []
    items = order.items.all()
    for item in items:
        converted_items.append({
            "variant": item.variant,  # Product name
            "quantity": item.quantity,
            "price": round(item.variant.price, 2),
            "discounted_price": round(item.variant.discounted_price, 2),
            "image_url": item.variant.images.first().image.url if item.variant.images.all() else None,
        })

    # Render the HTML email content
    user_html_content = render_to_string('order_confirm.html', {
        'order': order,
        'web_url':WEB_URL,
        'web_url_for_images':WEB_URL_FOR_IMAGES,
        'items': converted_items, 
    })

    # Email subject and sender/receiver details
    user_subject = 'Your Order is Confirmed! 🛍️'
    from_email = settings.DEFAULT_FROM_EMAIL
    admin_email = ADMIN_EMAIL

    # Create the email
    user_email_msg = EmailMultiAlternatives(user_subject, '', from_email, [user_email])
    user_email_msg.attach_alternative(user_html_content, "text/html")

    # Create the email
    if order.invoice:
        invoice_path = order.invoice.path  # This should give the absolute file path

        if os.path.exists(invoice_path): 
            user_email_msg.attach_file(invoice_path)  # Attach the invoice to the email
        else:
            print(f"Invoice file not found at {invoice_path}")

    # Send the email
    try:
        user_email_msg.send()
    except Exception as e:
        print(f"Error sending email: {e}") 

    admin_subject = "New Order Placed - Admin Notification"
    admin_html_content = render_to_string('order_confirm_admin.html', {
        'order': order,
        'items': converted_items, 
    })

    admin_email_msg = EmailMultiAlternatives(admin_subject, '', from_email, [admin_email])
    admin_email_msg.attach_alternative(admin_html_content, "text/html")

    # Send admin email
    try:
        admin_email_msg.send()
    except Exception as e:
        print(f"Error sending admin email: {e}")

    logger.info("Send succesfully")

def generate_transaction_id():
    digits_part = ''.join(random.choices(string.digits, k=3))
    chars_part = ''.join(random.choices(string.ascii_uppercase , k=5))
    current_date = datetime.now().strftime("%Y%m%d")
    return current_date + digits_part + chars_part

def check_promo_code(value):
    try:
        try:
            promo_code = Promotion.objects.get(coupon_code=value, is_active=True)
            return {'type':'promotion','object':promo_code}
        except Promotion.DoesNotExist:
            pass
        
    except Exception as e:
        print(str(e))
        return {'success':False,'message':"Can not find Promo code"}
    
def generate_invoice(email, order_number):
    try:
        # Fetch the order and associated user
        order = Order.objects.get(order_number=order_number)
        user = order.user  

        logger.info("Inside Invoice Generation")
        # Calculate values for the invoice
        gst_amount = order.gst  
        final_price = order.final_price
        formatted_date = order.order_date.strftime("%B %d, %Y")  # Format the date
        invoice_number = f"ICPIV{user.id}{order.id}"

        # Generate the HTML content for the invoice
        html_content = f"""
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Invoice</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background-color: #f7fafc;
                    padding: 20px;
                }}
                .invoice-container {{
                    max-width: 800px;
                    margin: 0 auto;
                    background-color: #fff;
                    padding: 20px;
                    border-radius: 8px;
                    box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
                }}
                .header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 20px;
                }}
                .header img {{
                    width: 120px;
                    height: 50px;
                }}
                .header .invoice-title {{
                    text-align: right;
                }}
                .header .invoice-title h1 {{
                    margin: 0;
                    font-size: 24px;
                    color: #1a202c;
                }}
                .header .invoice-title p {{
                    margin: 0;
                    font-size: 14px;
                }}
                .details p {{
                    margin: 0;
                    font-size: 14px;
                }}
                .details strong {{
                    font-weight: bold;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 20px;
                }}
                th, td {{
                    padding: 10px;
                    border: 1px solid #e2e8f0;
                    text-align: left;
                    font-size: 12px;
                }}
                th {{
                    background-color: #f7fafc;
                }}
                .totals td {{
                    border: none;
                    text-align: right;
                }}
            </style>
        </head>
        <body>
            <div class="invoice-container">
                <div class="header">
                    <img src="https://www.iconperfumes.in/_next/image/?url=%2Ficon_images%2Flogo.png&w=256&q=75" alt="Company Logo">
                    <div class="invoice-title">
                        <h1>INVOICE</h1>
                        <p>Invoice No: {invoice_number}</p>
                        <p>Date: { formatted_date }</p>
                    </div>
                </div>
                <div class="details">
                    <p><strong>Invoice To:</strong></p>
                    <p>{order.name}</p>
                    <p>{order.address}, {order.city}</p>
                    <p>{order.state}, {order.country}</p>
                </div>
                <div class="details">
                    <p><strong>Pay To:</strong></p>
                    <p>Icon Perfumes</p>
                    <p>Chandan Talawdi, Dariyapur, Ahmedabad, Gujarat</p>
                    <p>Pincode: 380001</p>
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>Product</th>
                            <th>Price</th>
                            <th>Quantity</th>
                            <th>Amount</th>
                        </tr>
                    </thead>
                    <tbody>
        """

        for item in order.items.all():
            price = item.variant.discounted_price * item.quantity
            html_content += f"""
                        <tr>
                            <td>{item.variant}</td>
                            <td>INR {"%.2f" % item.variant.discounted_price}</td>
                            <td>{item.quantity}</td>
                            <td>INR {"%.2f" % price}</td>
                        </tr>
            """

        html_content += f"""
                        <tr class="totals">
                            <td colspan="3"><strong>Discount:</strong></td>
                            <td>INR {order.discount}</td>
                        </tr>
                        <tr class="totals">
                            <td colspan="3"><strong>Sub Total:</strong></td>
                            <td>INR {order.sub_total}</td>
                        </tr>
                        <tr class="totals">
                            <td colspan="3"><strong>Total:</strong></td>
                            <td>INR {final_price}</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </body>
        </html>
        """

        with sync_playwright() as p:
            # Redirect logs to /dev/null
            if os.path.exists(EXUCUTABLE_PATH_CHROMIUM):
                browser = p.chromium.launch(
                    headless=True, 
                    executable_path=EXUCUTABLE_PATH_CHROMIUM
                )
            else:
                browser = p.chromium.launch(headless=True) 
                    
            page = browser.new_page()
            page.set_content(html_content)
            timestamp = datetime.now().strftime('%d%m%Y%H%M%S')
            pdf_file_path = os.path.join(settings.MEDIA_ROOT, 'invoices', f'invoice_{order.id}_{timestamp}.pdf')
            os.makedirs(os.path.dirname(pdf_file_path), exist_ok=True)
            page.pdf(path=pdf_file_path, format='A4')

            browser.close()

            save_order_in_thread(order, email, timestamp)
            
            return JsonResponse({"message": "Invoice generated successfully"})
    except Order.DoesNotExist:
        return JsonResponse({"error": "Error", "message": "Order does not exist"}, status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        print(str(e))
        logger.error(f"Error generating invoice for order {str(e)}")
        raise
    



from backend.settings import BASE_DIR

# def show_logs(request):
#     logs = ""
#     if request.user.is_staff:
#         with open(BASE_DIR / "logs/admin.log","r") as log:
#             logs = log.read()
#         return render(request, "admin_log.html", {"logs": logs})
#     else:
#         return render(request, "admin_log.html")

def show_logs(request):
    if request.user.is_staff or request.user.is_superuser:
        logs = ""
        try:
            log_file_path = os.path.join(BASE_DIR, "logs/admin.log")
            
            # Check if the log file exists and read it
            if os.path.exists(log_file_path):
                with open(log_file_path, "r") as log:
                    logs = log.read()
            else:
                logs = "No logs found."
        except Exception as e:
            logs = f"Error reading logs: {str(e)}"
        
        return render(request, "admin_log.html", {"logs": logs})
    else:
        return render(request, "admin_log.html", {"logs": "You are not authorized to view the logs."})

@api_view(['GET'])
def getBanners(request):
    try:
        cache_key = "banners"
        cached_data = cache.get(cache_key)
        # if cached_data:
        #     return Response(cached_data, status=status.HTTP_200_OK)
        
        banners = Banner.objects.all()
        if not banners.exists():
            return Response({"error":"Error",'message':'There are no banners'},status=status.HTTP_400_BAD_REQUEST)
        
        serializer =  BannerSerializer(banners,many=True)
        response_data = {'success':True,'banners':serializer.data}
        cache.set(cache_key, response_data, timeout=60 * 10)
        
        return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        print(str(e))
        return Response({"error":"Error",'message':f"Internal server error:- {str(e)}"},status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def getPromocodes(request):
    try:
        cache_key = "promotions"
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data, status=status.HTTP_200_OK)
        
        promotions = Promotion.objects.all()
        if not promotions.exists():
            return Response({'success':False,'message':f"There are no promotions available."},status=status.HTTP_200_OK)
        serializer = PromotionSerializer(promotions,many=True)

        response_data = {'success':True,'promotions':serializer.data}
        cache.set(cache_key, response_data, timeout=60 * 10)
        return Response(cache_key,status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error":"Error",'message':f"Internal server error"},status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@permission_classes([IsAuthenticated])
@api_view(["POST"])
def subscribe_news_letter(request):
    try:
        data = json.loads(request.body)
        email = data.get('email')

        if not email:
            return Response({'error':"Error","message":"Please enter email"})
        
        try:
            news = NewsLetter.objects.get(email=email)
            return Response({'error':"Error","message":"Email already subscribed"},status=status.HTTP_400_BAD_REQUEST)
        except NewsLetter.DoesNotExist:
            news_letter = NewsLetter(email=email)
            news_letter.save()
            html_content = f"""
                <!DOCTYPE html>
                <html lang="en">
                <head>
                <meta charset="UTF-8" />
                <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
                <title>Subscription Confirmation</title>
                <style>
                    body {{
                    font-family: Arial, sans-serif;
                    background-color: #f4f4f4;
                    margin: 0;
                    padding: 0;
                    }}
                    .container {{
                    max-width: 600px;
                    margin: 40px auto;
                    background-color: #ffffff;
                    padding: 30px;
                    border-radius: 8px;
                    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
                    }}
                    .banner {{
                    width: 100%;
                    height: auto;
                    border-radius: 8px 8px 0 0;
                    display: block;
                    }}
                    .content {{
                    text-align: center;
                    padding: 20px 0;
                    }}
                    .title {{
                    font-size: 28px;
                    font-weight: bold;
                    color: #333;
                    margin-bottom: 10px;
                    }}
                    .subtitle {{
                    font-size: 16px;
                    color: #555;
                    margin-bottom: 20px;
                    }}
                    .message {{
                    font-size: 16px;
                    color: #666;
                    line-height: 1.5;
                    margin-bottom: 30px;
                    }}
                    .button {{
                    display: inline-block;
                    background-color: #433224;
                    color: #ffffff;
                    text-decoration: none;
                    padding: 12px 25px;
                    border-radius: 5px;
                    font-size: 16px;
                    font-weight: 600;
                    margin: 20px 0;
                    }}
                    .footer {{
                    font-size: 12px;
                    color: #888;
                    text-align: center;
                    margin-top: 20px;
                    }}
                </style>
                </head>
                <body>
                <div class="container">
                <div style="background-color: #FFFBF3; text-align: center; padding: 50px; font-weight: 500;">
                    <img src="https://www.iconperfumes.in/_next/image/?url=%2Ficon_images%2Flogo.png&w=256&q=75" alt="Logo" style="height: 51px; width: 132px; object-fit: contain; margin-bottom: 20px;">
                    <h1 style="color: black; font-size: 24px; margin: 0;">Welcome to the Icon Perfumes Family!</h1>
                </div>

                <!-- Content -->
                <div class="content">
                    <p class="message">
                    You’ve successfully subscribed to our exclusive newsletter!  
                    Stay tuned for the latest updates, fragrance tips, and special announcements delivered straight to your inbox.
                    </p>
                    <a href="https://www.iconperfumes.in/shop/" class="button">Start Shopping</a>
                </div>

                <p style="font-size: 16px; line-height: 1.5; color: #666; border-bottom: 1px dashed #666; padding-bottom: 20px;">
                    Thanks for being part of our family!
                </p>

                <!-- Footer -->
                <div class="footer">
                    <p>- Team Icon Perfumes</p>
                    <p>&copy; {current_year} Icon Perfumes. All rights reserved.</p>
                </div>
                </div>
                </body>
                </html>

            """
            send_email_task(
                subject=" You’re In! Welcome to Icon Perfumes 💌",
                message='',
                html_message=html_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email]
            )
            return Response({'success':True,'message':"News Letter subscribed successfully"},status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'success':False,'message':f'Something Went Wrong {e}'},status=status.HTTP_200_OK)

@permission_classes([IsAuthenticated])
@api_view(['POST'])
def unsubscribe_newsletter(request):
    data = json.loads(request.body)
    email = data.get('email')
    
    if not email:
        return Response({'error':"Error","message":"Please enter email"},status=status.HTTP_400_BAD_REQUEST)
    
    try:
        news = NewsLetter.objects.get(email=email)
        news.delete()
        return Response({'success':True,'message':"You have successfullly unsubscribed"},status=status.HTTP_200_OK)

    except NewsLetter.DoesNotExist:
        return Response({'error':'Error','message':"Subscribe first"},status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def contact_us(request):
    try:
        data = json.loads(request.body)

        name = data.get('name')
        email = data.get('email')
        phone = data.get('phone')
        subject = data.get('subject')
        message = data.get('message')

        contact = ContactUs(
            name=name,
            email=email,
            phone=phone,
            subject=subject,
            message=message
        )
        contact.save()
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Contact Inquiry Confirmation</title>
        <style>
            body {{
            font-family: Arial, sans-serif;
            background-color: #f4f4f4;
            margin: 0;
            padding: 0;
            }}
            .container {{
            max-width: 600px;
            margin: 30px auto;
            background-color: #ffffff;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            text-align: center;
            }}
            .header {{
            background-color: #FFFBF3;
            color: #000;
            padding: 20px;
            border-radius: 8px 8px 0 0;
            }}
            .header img {{
            max-height: 50px;
            }}
            .header h1 {{
            margin: 10px 0;
            font-size: 22px;
            font-weight: bold;
            }}
            .content {{
            margin: 20px 0;
            }}
            .content h2 {{
            color: #007b83;
            font-size: 20px;
            margin-bottom: 10px;
            }}
            .content p {{
            color: #555;
            font-size: 14px;
            line-height: 1.6;
            }}
            .details {{
            text-align: left;
            margin: 20px 0;
            font-size: 14px;
            color: #333;
            padding: 20px;
            background-color: #f9f9f9;
            border-radius: 5px;
            }}
            .details p {{
            margin: 10px 0;
            }}
            .details p span {{
            font-weight: bold;
            color: #007b83;
            }}
            .footer {{
            margin-top: 30px;
            font-size: 12px;
            color: #888;
            text-align: center;
            }}
            .footer a {{
            color: #007b83;
            text-decoration: none;
            font-weight: bold;
            }}
        </style>
        </head>
        <body>
        <div class="container">
            <!-- Header Section -->
            <div class="header">
            <img src="https://www.iconperfumes.in/_next/image/?url=%2Ficon_images%2Flogo.png&w=256&q=75" alt="Your Logo">
            <h1>Hello {name},</h1>
            </div>

            <!-- Content Section -->
            <div class="content">
            <p>
                Dear <strong>{name}</strong>,<br>
                Thank you for reaching out to us! We’ve received your inquiry and will get back to you within 24-48 hours. 
                Our team is here to help with any questions regarding our premium prefumes/attars, orders, or policies. If your inquiry is urgent, 
                feel free to send us a mail at <a href="mailto:info@iconperfumes.in" style="color:#433224">info@iconperfumes.in</a>. 
            </p>
            </div>
            <p style=" 
            color: #555;
            font-size: 14px;
            line-height: 1.6;
            color: #666;
            border-bottom:1px;
            border-bottom-color: #666;
            border-bottom-style: dashed;
            padding-top:20px;
            padding-bottom:20px
            ">We appreciate your interest and look forward to assisting you.</p>

            <!-- Footer Section -->
            <div class="footer">
            <p>
                Best Regards,<br>
                Team Icon Perfumes
            </p>
            <p>&copy; {current_year} Icon Perfumes. All rights reserved.</p>
            </div>
        </div>
        </body>
        </html>
        """
        send_email_task(
                subject=f"We Received Your Message!",
                message='',  # Fallback text-only version
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                html_message=html_content,  # HTML version of the email
            )

        admin_html_message = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>New Contact Inquiry</title>
            </head>
            <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; margin: 0; padding: 0;">
            <div style="max-width: 600px; margin: 30px auto; background-color: #ffffff; padding: 30px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1); text-align: center;">
                <!-- Header Section -->
                <div style="background-color: #FFFBF3; color: #ffffff; padding: 20px; border-radius: 8px 8px 0 0;">
                <img src="https://www.iconperfumes.in/_next/image/?url=%2Ficon_images%2Flogo.png&w=256&q=75" alt="Icon Perfumes" style="max-height: 50px;">
                </div>

                <!-- Content Section -->
                <div style="margin: 20px 0;">
                <h1 style="margin: 10px 0; font-size: 22px; font-weight: bold;">Hello Admin,</h1>
                <p style="color: #555; font-size: 14px; line-height: 1.6;">
                A new inquiry has been submitted via the "Contact Us" page. Below are the details: 
                </p>
                </div>

                <!-- User Details Section -->
                <div style="text-align: left; margin: 20px 0; font-size: 14px; color: #333; padding: 20px; background-color: #f9f9f9; border-radius: 5px;">
                <p style="margin: 10px 0;"><span style="font-weight: bold; color: #433224;">Name:</span> {name}</p>
                <p style="margin: 10px 0;"><span style="font-weight: bold; color: #433224;">Email:</span> {email}</p>
                <p style="margin: 10px 0;"><span style="font-weight: bold; color: #433224;">Phone:</span> {phone}</p>
                <p style="margin: 10px 0;"><span style="font-weight: bold; color: #433224;">Subject:</span> {subject}</p>
                <p style="margin: 10px 0;"><span style="font-weight: bold; color: #433224;">Message:</span> {message}</p>
                </div>

                <p style="color: #555; font-size: 14px; line-height: 1.6; color: #666; border-bottom: 1px dashed #666; padding-top: 20px; padding-bottom: 20px;">
                Please review and respond to the user at your earliest convenience. 
                </p>
                
                <p style="color:#555; font-size:14px; line-height: 1.6;>
                    Thanks, <br>
                    Icon Perfumes Team 
                </p>
                <!-- Footer Section -->
                <div style="margin-top: 30px; font-size: 12px; color: #888; text-align: center;">
                <p>&copy; {current_year} Icon Perfumes. All rights reserved.</p>
                </div>
            </div>
            </body>
            </html>
        """
        send_email_task.delay(
                subject=f"New Inquiry from Icon Perfumes Website ",
                message='',  # Fallback text-only version
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[ADMIN_EMAIL],
                html_message=admin_html_message,  # HTML version of the email
        )

        return Response({'success':True,'message':'Successfully Submitted'},status=status.HTTP_200_OK)
    except Exception as e:
        print(str(e))
        return Response({'error':'Error','message':'Internal Server Error'},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

def serve_invoices(request, path):
    if not request.user.is_staff:
        return HttpResponseForbidden("You are not Authenticated")
    
    invoice_path = os.path.join(settings.MEDIA_ROOT,'invoices',path)
    if os.path.exists(invoice_path):
        with open(invoice_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/octet-stream')
            response['Content-Disposition'] = f'inline; filename={os.path.basename(invoice_path)}'
            return response
    else:
        return HttpResponseForbidden("File Not Found")

from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated
from rest_framework.response import Response
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    """
    Changing the default exception handler of DRF to show message on frontend
    """
    # Get the default response
    response = exception_handler(exc, context)

    if isinstance(exc, AuthenticationFailed):
        return Response(
            {"success": False, "message": "Session Expired. Please log in again."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    if isinstance(exc, NotAuthenticated):
        return Response(
            {"success": False, "message": "Session Expired. Please Login Again"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    return response

def get_user_from_jwt(request):
    token = request.COOKIES.get('token') if request else None  # Get JWT token from cookie
    if not token:
        return None

    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=['HS256'])
        user_id = payload.get('user_id')
        user = User.objects.get(id=user_id)
        return user
    except (jwt.ExpiredSignatureError, jwt.DecodeError, User.DoesNotExist):
        return None

@shared_task
def send_email_task(subject, message, from_email, recipient_list, html_message):
    send_mail(
        subject=subject,
        message=message,  # Fallback text-only version
        from_email=from_email,
        recipient_list=recipient_list,
        html_message=html_message,  # HTML version of the email
    )