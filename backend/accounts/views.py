import random
import string
import json
import traceback

from django.http import JsonResponse
import jwt
import hashlib
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import api_view, APIView, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import authenticate,logout, login
from rest_framework.response import Response
from django.core.mail import send_mail
from django.shortcuts import redirect 
from rest_framework import status
from datetime import timezone, timedelta
from django.conf import settings
from datetime import datetime
from django.db.models import Q
from .serializers import *
from .models import *
from mainapp.models import Cart , ProductVariant , Wishlist
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
from dotenv import load_dotenv
import os
from decouple import config
from decouple import Config, RepositoryEnv
try:
    config = Config(RepositoryEnv('/var/www/icon_perfumes/backend/.env'))
except:
    pass

load_dotenv(settings.BASE_DIR / '.env')

BASE_URL = config('WEB_URL') + "/login/reset-password/"
current_year = datetime.now().year
OTP_HEADER = "Your Sign-in Code"
OTP_SUBJECT = "Here is your verification code"

def hash_otp(otp):
    '''
    Returns the hash of the otp
    '''
    return hashlib.sha256(otp.encode()).hexdigest()

@api_view(["POST"])
def signup(request):
    try:
        data = json.loads(request.body)  # Get all data from body
        email =  data.get('email','')
        name = data.get('name','')
        password = data.get('password','')
        phone_number = data.get('phone_number','')

        # Check if detail is empty or not
        if not email or not password or not phone_number:
            data = {'error':"Error","message":"Please provide all required fields"}
            return Response(data,status=status.HTTP_400_BAD_REQUEST)
        data = {'success':True}

        # Now Check user with email already exists or not
        try:
            email_exists = CustomUser.objects.get(email=email)
            if email and email_exists:
                return Response({'error':"Error",'message':'User with this email already exists'},status = status.HTTP_409_CONFLICT)
        except Exception as e:
            pass
        try:
            phone_exists = CustomUser.objects.get(phone_number=phone_number)
            if phone_number and phone_exists:
                return Response({'error':"Error",'message':'User with this phone number already exists'},status = status.HTTP_409_CONFLICT)
        except Exception as e:
            pass

        # If not exists then create new user
        user = CustomUser(email=email)
        user.name = name
        user.phone_number = phone_number
        user.is_active = False
        user.set_password(password)
        user.save()

        # Generate otp
        otp = str(random.randint(100000,999999))
        otpObj, created = Otp.objects.update_or_create(user=user,otp=hash_otp(otp))
        otpObj.otp = hash_otp(otp)
        otpObj.save()

        email_html = f""" 
        <!DOCTYPE html>
        <html lang="en">
        <head>
          <meta charset="UTF-8" />
          <meta name="viewport" content="width=device-width, initial-scale=1.0" />
          <title>{ OTP_HEADER }</title>
        </head>
        <body style="font-family: Arial, sans-serif; background-color: #f7f7f7; margin: 0; padding: 0;">
          <div style="max-width: 600px; background-color: #ffffff; margin: 40px auto; padding: 20px; border-radius: 10px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);">
            
            <!-- Header -->
            <div style="background-color: #FFFBF3; border-radius: 10px 10px 0 0; text-align: center; padding: 20px;">
              <img src="https://www.iconperfumes.in/_next/image/?url=%2Ficon_images%2Flogo.png&w=256&q=75" alt="Icon Perfumes Logo" style="height: 50px; object-fit: contain;" />
            </div>
            
            <!-- Content -->
            <div style="text-align: center; padding: 20px;">
              <h2 style="font-size: 24px; color: #333; margin: 20px 0;">
                Complete Your Registration
              </h2>
              <p style="font-size: 16px; color: #666;">Please enter the following confirmation code to complete your account setup:</p>
              
              <div style="padding: 15px; background-color: #f1f1f1; border-radius: 8px; margin: 20px 0; font-size: 28px; font-weight: bold; color: #333;">
                { otp }
              </div>
              
              <p style="font-size: 14px; color: #999;">
                If you didn’t request this, please ignore this message.
              </p>
            </div>
            
            <!-- Footer -->
            <div style="font-size: 12px; color: #999; text-align: center; border-top: 1px solid #eee; padding: 10px 0;">
              &copy; { current_year } Icon Perfumes. All rights reserved.
            </div>
          </div>
        </body>
        </html>
        """
        send_mail(
            subject=OTP_SUBJECT,
            html_message=email_html,
            message='',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
        )
        masked_email = get_masked_email(email)

        return Response(
            {"success": True, "message": f"OTP sent to {masked_email} email successfully.","email":email,"masked_email":masked_email},
            status=status.HTTP_201_CREATED
        )
    except Exception as e:
        return Response(
            {'error':"Error","message":f"Internal Server Error : {e}"},status=status.HTTP_500_INTERNAL_SERVER_ERROR)


        
# This code is for login with password 
@api_view(["POST"])
def user_login(request):
    try:
    # Get Data now if method is correct
        data = json.loads(request.body)
        identifier = str(data.get('phone_number'))
        password = data.get('password')
        if not identifier or not password:
          return Response({'error':"Error","message":'please enter phone number/email or password'},status=status.HTTP_400_BAD_REQUEST)
            
        # Search user with email and password
        if '@' in identifier:
            user = CustomUser.objects.get(email=identifier)
            if user and user.check_password(password):
                pass
            else:
                user = None
        else:
            user = CustomUser.objects.get(phone_number=identifier)
            if user and user.check_password(password):
                pass
            else:
                user = None
        
        if user:
            if user.is_active: # Logging in user with password 
                refresh  = RefreshToken.for_user(user) 
                cart_data = data.get('cart_data')
                wishlist_data = data.get('wishlist_data')
                if cart_data: 
                  for item in cart_data :
                      variant_id = item['variant'].get('id')
                      quantity = item.get('quantity')
                      variant = ProductVariant.objects.get(id=variant_id)
              
                      user_cart, created = Cart.objects.get_or_create(user=user,variant=variant)
                      if created:
                        user_cart.quantity =  int(quantity)
                      else:
                        user_cart.quantity += int(quantity)
                      user_cart.save()
        

                if wishlist_data:
                    for item in wishlist_data:
                      variant_id = item['variant'].get('id')
                      variant = ProductVariant.objects.get(id=variant_id)
                      user_wishlist, created = Wishlist.objects.get_or_create(user=user,variant=variant)
                      user_wishlist.save()
                
                is_localhost = bool(settings.DEBUG)

                response = JsonResponse({'success':True,"message":"Login Successfully"})
                response.set_cookie(
                    key="token",
                    value=str(refresh.access_token),
                    # httponly=True,
                    secure=False if is_localhost else True,
                    samesite="Lax" if is_localhost else "None",
                    domain=None if is_localhost else os.environ.get('DOMAIN'),
                    expires=timezone.now() + timedelta(days=30)
                )
                return response
            else:
                otp = str(random.randint(100000,999999))
                try:
                    otpObj = Otp.objects.get(user=user)
                    otpObj.otp = hash_otp(otp)
                    otpObj.save()
                except Otp.DoesNotExist:
                    otpObj = Otp.objects.create(user=user,otp=hash_otp(otp))


                email_html = f""" 
                    <!DOCTYPE html>
                    <html lang="en">
                    <head>
                    <meta charset="UTF-8" />
                    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
                    <title>{OTP_HEADER}</title>
                    </head>
                    <body style="font-family: Arial, sans-serif; background-color: #f7f7f7; margin: 0; padding: 0;">
                    <div style="max-width: 600px; background-color: #ffffff; margin: 40px auto; padding: 3vw; border-radius: 2vw; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);">

                        <!-- Header -->
                        <div style="background-color: #FFFBF3; border-radius: 2vw 2vw 0 0; text-align: center; padding: 20px;">
                        <img src="https://www.iconperfumes.in/_next/image/?url=%2Ficon_images%2Flogo.png&w=256&q=75" 
                            alt="Icon Perfumes Logo" style="height: 51px; width: 132px; object-fit: contain;" />
                        </div>

                        <!-- Content -->
                        <div style="text-align: center;">
                        <h2 style="font-size: 24px; color: #333; margin-bottom: 20px;">Email Verification Code</h2>
                        <p style="font-size: 16px; line-height: 1.5; color: #666;">
                            Please use the code below to verify your email address and complete your account setup:
                        </p>

                        <div style="padding: 20px; background-color: #f1f1f1; border-radius: 10px; margin-bottom: 20px; font-size: 36px; font-weight: bold; color: #333; text-align: center;">
                            {otp}
                        </div>

                        <p style="font-size: 16px; line-height: 1.5; color: #666; border-bottom: 1px dashed #666; padding-top: 20px; padding-bottom: 20px;">
                            Didn’t request this email? You can safely ignore it.
                        </p>
                        </div>

                        <!-- Footer -->
                        <div style="font-size: 12px; color: #888; text-align: center;">
                        <p>This email was sent to you because you started signing up for an account at Icon Perfumes.</p>
                        <p>&copy; {current_year} Icon Perfumes. All rights reserved.</p>
                        </div>
                    </div>

                    <!-- Mobile Styles -->
                    <style>
                        @media (max-width: 600px) {{
                            .container {{
                                margin: 20px;
                            }}
                            .header, .content, .footer {{
                                text-align: left;
                            }}
                            @media (max-width: 499px) {{
                                div {{
                                    padding: 4vw;
                                    margin: 20px;
                                    border-radius: 3vw;
                                }}
                                .otp-box {{
                                    font-size: 30px;
                                    padding: 15px;
                                }}
                                .footer {{
                                    font-size: 11px;
                                }}
                            }}
                        }}
                    </style>
                    </body>
                    </html>
                """
                send_mail(
                    subject="Your Sign-in Code",
                    html_message=email_html,
                    message='',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                ) 
                
                masked_email = get_masked_email(user.email)
                message = f'OTP successfully sent to your Email {masked_email}'
                return Response({'success':False,'verify':False,"message":'You Are Not Verified Please Verify Your Email','email':user.email,'masked_email':masked_email},status=status.HTTP_200_OK)
        else:
            # Authentication failed or password invalid
            data = {'error':"Error",'message':'phone number/email or password incorrect'}
            return Response(data,status=status.HTTP_400_BAD_REQUEST)
    except json.JSONDecodeError:
        return Response(
            {"error":"Error","message":"Invalid request format"},
            status=status.HTTP_400_BAD_REQUEST
        )
    except CustomUser.DoesNotExist:
        return Response(
            {'error':"Error",'message':"User with this email/phone number does not exists"}
            ,status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response(
            {'error':"Error",'message':f"Internal Server Error:- {str(e)}"}
            ,status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(["POST"])
def verify_otp(request):
    try:
        data = json.loads(request.body)
        identifier = data.get('email','')
        otp = data.get('otp','')
        
        if not identifier or not otp:
            return Response(
                {"error": "Error", "message": "Email/Phone Number and OTP are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if '@' in identifier:
            user = CustomUser.objects.get(email=identifier)
        else:
            user = CustomUser.objects.get(phone_number=identifier)

        # Retrieve OTP from cache
        otpObj = Otp.objects.get(user=user)
        if hash_otp(str(otp)) != otpObj.otp or not otpObj.is_valid:
            return Response(
                {"error": "Error", "message": "Invalid or expired OTP."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Activate user account
        user.is_active = True
        user.save()

        if data.get('data'):
          wishlist_data = data['data'].get('wishlist_data')
          cart_data = data['data'].get('cart_data')

          if cart_data:
            for item in cart_data :
                variant_id = item['variant'].get('id')
                quantity = item.get('quantity')

                variant = ProductVariant.objects.get(id=variant_id)
                
                user_cart, created = Cart.objects.get_or_create(user=user,variant=variant)
                if not created:
                    user_cart.quantity +=  int(quantity)
                else:
                    user_cart.quantity += int(quantity)
                user_cart.save()
          
          if wishlist_data:
              for item in wishlist_data:
                  variant_id = item['variant'].get('id')
                  variant = ProductVariant.objects.get(id=variant_id)
                  user_wishlist, created = Wishlist.objects.get_or_create(user=user,variant=variant)
                  user_wishlist.save()
              
        # Clear OTP from cache
        otpObj.delete()
            
        email_html = f""" 
          <!DOCTYPE html>
          <html lang="en">
          <head>
            <meta charset="UTF-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1.0" />
            <title>Welcome to Icon Perfumes</title>
            <style>
              @media (max-width: 499px) {{
                body {{
                  font-size: 14px !important;
                }}
                .container {{
                  margin: 20px auto;
                  padding: 4vw !important;
                  border-radius: 3vw !important;
                }}
                .logo {{
                  font-size: 20px !important;
                }}
                .content h2 {{
                  font-size: 20px !important;
                }}
                .footer {{
                  font-size: 11px !important;
                }}
              }}
            </style>
          </head>
          <body style="font-family: Arial, sans-serif; background-color: #f7f7f7; margin: 0; padding: 0;">
            <div style="max-width: 600px; background-color: #fff; margin: 40px auto; padding: 20px; border-radius: 10px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);">
              
              <!-- Header -->
              <div style="background-color: #FFFBF3; border-radius: 2vw 2vw 0 0; text-align: center; padding: 20px;">
                <img src="https://www.iconperfumes.in/_next/image/?url=%2Ficon_images%2Flogo.png&w=256&q=75" alt="Icon Perfumes Logo" style="height: 51px; width: 132px; margin-bottom: 30px; object-fit: contain;" />
              </div>
              
              <!-- Content -->
              <div style="text-align: left;">
                <h2 style="font-size: 24px; color: #333; margin-bottom: 20px;">
                  Welcome to Icon Perfumes, {user.name}!
                </h2>
                <p style="font-size: 16px; line-height: 1.5; color: #666; margin-bottom: 20px;">
                  We’re excited to have you join our community. At Icon Perfumes, we celebrate elegance and sophistication through our carefully curated collection of exquisite fragrances.
                </p>
                <p style="font-size: 16px; line-height: 1.5; color: #666; margin-bottom: 20px;">
                  As a valued member, you’ll be the first to know about our latest arrivals, exclusive collections, and special events. We're here to help you find the perfect scent to express your unique style.
                </p>
                <p style="font-size: 16px; line-height: 1.5; color: #666;">
                  Feel free to explore our collection and reach out if you have any questions or need assistance.
                </p>
              </div>
              
              <!-- Footer Banner -->
              <div style="text-align: center; margin-top: 20px;">
                <img src="https://www.iconperfumes.in/icon_images/appointment_banner.webp" alt="Discover Icon Perfumes" style="width: 100%; border-radius: 10px; margin-bottom: 20px;" />
              </div>
              
              <!-- Call to Action -->
              <div style="text-align: center; margin-bottom: 20px;">
                <a href="https://www.iconperfumes.in/shop/" style="display: inline-block; background-color: #433224; color: #fff; text-decoration: none; padding: 12px 24px; border-radius: 5px; font-weight: bold;">
                  Start Exploring
                </a>
              </div>
              
              <!-- Footer -->
              <div style="font-size: 12px; color: #888; text-align: left; border-top: 1px solid #eee; padding-top: 10px;">
                <p>We’re glad to have you with us. If you ever need assistance, feel free to reply to this email or visit our website for more information.</p>
                <p style="margin: 10px 0;">&copy; {current_year} Icon Perfumes. All rights reserved.</p>
                <p>- Team Icon Perfumes</p>
              </div>
            </div>
          </body>
          </html>

        """
        if user.is_new == True:
          send_mail(
              subject="Welcome to Icon Perfumes! 🎉",
              html_message=email_html,
              message='',
              from_email=settings.DEFAULT_FROM_EMAIL,
              recipient_list=[user.email],
          )
        user.is_new = False
        user.save()
        refresh = RefreshToken.for_user(user)   
        token = str(refresh.access_token)
        response = JsonResponse({"success": True, "message": "Email verified successfully."},status=status.HTTP_200_OK)
        is_localhost = bool(settings.DEBUG)
        response.set_cookie(
            key="token",
            value=token,
            # httponly=True,
            secure=False if is_localhost is True else True,
            samesite="Lax" if is_localhost is True else "None",
            domain= None if is_localhost is True else os.environ.get("DOMAIN"),
            expires=timezone.now() + timedelta(days=30)
        )
        return response
    except CustomUser.DoesNotExist:
        return Response(
            {"error": "Error", "message": "User not found."},
            status=status.HTTP_404_NOT_FOUND
        )
                
    except Otp.DoesNotExist:
        return Response(
            {'error':"Error",'message':f"OTP is invalid or expired"}
            ,status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        traceback.print_exc()
        return Response(
            {'error':"Error",'message':f"Internal Server Error:- {str(e)}"}
            ,status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def get_masked_email(email):
    name, domain = email.split('@')
    
    if len(name) > 3:
        masked_email = name[0] + '*' * (len(name) - 3) + name[-2:] + '@' + domain
    elif len(name) == 3:
        masked_email = name[0] + '*' + name[-1] + '@' + domain
    else:
        masked_email = '*' * len(name) + '@' + domain  # Mask fully if very short
    
    return masked_email


@api_view(['POST'])
def send_otp(request):
    try:
        data = json.loads(request.body)
        identifier = data.get('email')
        if not identifier:
            return Response({
                'error':"Error", 'message':'Email/Phone Number is required'
            },status=status.HTTP_400_BAD_REQUEST)
        
        if '@' in identifier:
            user = CustomUser.objects.get(email=identifier)
        else:
            user = CustomUser.objects.get(phone_number=identifier)

        
        today = timezone.now().date()
        otpObj = Otp.objects.get(user=user)
        if otpObj.updated_at.date() < today:
            otpObj.count = 1
            otpObj.save()
        elif otpObj.count >= 5:
            return Response({
                'error':"Error", 'message':'You can send upto 5 OTPs in a day please try again tomorrow.'
            },status=status.HTTP_400_BAD_REQUEST)
        
        otp = str(random.randint(100000,999999))
        try:
            otpObj = Otp.objects.get(user=user)
            otpObj.otp = hash_otp(otp)
            otpObj.count += 1
            otpObj.save()
        except Otp.DoesNotExist:
            otpObj = Otp.objects.create(user=user,otp=hash_otp(otp))


        email_html = f""" 
        <!DOCTYPE html>
        <html lang="en">
        <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>{OTP_HEADER}</title>
        </head>
        <body style="font-family: Arial, sans-serif; background-color: #f7f7f7; margin: 0; padding: 0;">
        <div style="max-width: 600px; background-color: #ffffff; margin: 40px auto; padding: 3vw; border-radius: 2vw; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);">

            <!-- Header -->
            <div style="background-color: #FFFBF3; border-radius: 2vw 2vw 0 0; text-align: center; padding: 20px;">
            <img src="https://www.iconperfumes.in/_next/image/?url=%2Ficon_images%2Flogo.png&w=256&q=75" 
                alt="Icon Perfumes Logo" style="height: 51px; width: 132px; object-fit: contain;" />
            </div>

            <!-- Content -->
            <div style="text-align: center;">
            <h2 style="font-size: 24px; color: #333; margin-bottom: 20px;">Email Verification Code</h2>
            <p style="font-size: 16px; line-height: 1.5; color: #666;">
                Please use the code below to verify your email address and complete your account setup:
            </p>

            <div style="padding: 20px; background-color: #f1f1f1; border-radius: 10px; margin-bottom: 20px; font-size: 36px; font-weight: bold; color: #333; text-align: center;">
                {otp}
            </div>

            <p style="font-size: 16px; line-height: 1.5; color: #666; border-bottom: 1px dashed #666; padding-top: 20px; padding-bottom: 20px;">
                Didn’t request this email? You can safely ignore it.
            </p>
            </div>

            <!-- Footer -->
            <div style="font-size: 12px; color: #888; text-align: center;">
            <p>This email was sent to you because you started signing up for an account at Icon Perfumes.</p>
            <p>&copy; {current_year} Icon Perfumes. All rights reserved.</p>
            </div>
        </div>

        <!-- Mobile Styles -->
        <style>
            @media (max-width: 600px) {{
                .container {{
                    margin: 20px;
                }}
                .header, .content, .footer {{
                    text-align: left;
                }}
                @media (max-width: 499px) {{
                    div {{
                        padding: 4vw;
                        margin: 20px;
                        border-radius: 3vw;
                    }}
                    .otp-box {{
                        font-size: 30px;
                        padding: 15px;
                    }}
                    .footer {{
                        font-size: 11px;
                    }}
                }}
            }}
        </style>
        </body>
        </html>

        """
        send_mail(
            subject=OTP_SUBJECT,
            html_message=email_html,
            message='',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
        )

        masked_email = get_masked_email(user.email)
        message = f'OTP successfully sent to your Email {masked_email}'
            
        return Response({'success':True,'email':user.email,'masked_email':masked_email,"message": message},status=status.HTTP_200_OK)

    except CustomUser.DoesNotExist:
        return Response(
            {"error": "Error", "message": "User not found."},
            status=status.HTTP_404_NOT_FOUND
        )
                
    except Otp.DoesNotExist:
        return Response(
            {'error':"Error",'message':f"OTP is invalid or expired"}
            ,status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response(
            {'error':"Error",'message':f"Internal Server Error:- {str(e)}"}
            ,status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
#function to generate a random token
def generate_token():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=6))

@api_view(['POST'])
def forgot_password(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        email = data.get('email')

        try:
            user = CustomUser.objects.get(email=email)
            if not user:
                return Response({"success":False,'message':'User with this email not found'},status=status.HTTP_404_NOT_FOUND)

            reset_token = generate_token()
            user.reset_password_token = reset_token
            user.save()

            reset_link = BASE_URL + f"{reset_token}/"
            subject = 'Reset Your Password – Icon Perfumes 🔒 '
            html_message = f"""
            <html lang="en">
            <head>
              <meta charset="UTF-8">
              <meta name="viewport" content="width=device-width, initial-scale=1.0">
              <title>Reset Password Email</title>
              <style>
                body {{
                  font-family: Arial, sans-serif;
                  background-color: #f7f6f1;
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
                  text-align: center;
                }}
                .header {{
                  background-color: #FFFBF3;
                  padding: 20px;
                  border-radius: 8px 8px 0 0;
                }}
                .header img {{
                  max-width: 150px;
                  height: 55px;
                  object-fit: contain;
                }}
                .title {{
                  margin-top: 18px;
                  font-size: 24px;
                  font-weight: bold;
                  color: #333;
                  margin-bottom: 10px;
                }}
                .subtitle {{
                  font-size: 16px;
                  color: #666;
                  margin-bottom: 30px;
                }}
                .message {{
                  font-size: 16px;
                  color: #333;
                  margin-bottom: 30px;
                  line-height: 1.5;
                }}
                .button{{
                  display: inline-block;
                  background-color:#FFFBF3;
                  color: #ffffff;
                  text-decoration: none;
                  padding: 12px 20px;
                  border-radius: 5px;
                  font-size: 16px;
                  font-weight: 600px;
                  margin-top: 20px;
                }}
                .footer {{
                  font-size: 12px;
                  color: #888;
                  margin-top: 30px;
                }}
              </style>
            </head>
            <body>
              <div class="container">
                <!-- Header -->
                <div class="header">
                  <img src="https://www.iconperfumes.in/_next/image/?url=%2Ficon_images%2Flogo.png&w=256&q=75" alt="Company Logo">
                </div>
                <!-- Title -->
                <div class="title">Hi {user.name}, </div>
                <!-- Subtitle -->
                <!-- Message -->
                <div class="message">
                  We received a request to reset your password for your Icon Perfumes account. Click the button below to set a new password. 
                </div>
                <!-- Button -->
                <a href="{reset_link}" class="button" style="text-decoration: none; color:#000;">Reset Your Password</a>
                
                      <p style="font-size: 16px; line-height: 1.5; color: #666;   border-bottom:1px;
                                    border-bottom-color: #666;
                                    border-bottom-style: dashed;
                                      padding-top:10px;
                                    padding-bottom:20px;">If you didn’t request this, you can safely ignore this email. Your current password will remain unchanged. </p>
                <!-- Footer -->
                <div class="footer">
                  For any issues, feel free to reach out to our support team. On info@iconperfumes.in <br>
                  Stay stylish, <br>
                  Team Icon Perfumes <br> 
                  &copy; {current_year} Icon Perfumes. All rights reserved..
                </div>
              </div>
            </body>
            </html>
            """
            send_mail(
                subject,
                '',
                settings.DEFAULT_FROM_EMAIL,
                [email],
                html_message=html_message,
                fail_silently=False
            )
            data = {
                'success':True,"message":'Please Check your email for reset password'}
            return Response(data,status=status.HTTP_200_OK)
        
        except CustomUser.DoesNotExist:
            data = {'error':'Error','message':'No user found with this phone number'}
            return Response(data,status=status.HTTP_404_NOT_FOUND)      
    else:
        data = {'error':"Error","message":"Method not allowed"}
        return Response(data,status=status.HTTP_405_METHOD_NOT_ALLOWED)

@api_view(['POST'])
def reset_password(request,token):
    try:
        user = CustomUser.objects.get(reset_password_token=token)
    except CustomUser.DoesNotExist:
        return Response({'error':"Error","message":'user not found'},status=status.HTTP_404_NOT_FOUND)
    try:
        if request.method == 'POST':
            data = json.loads(request.body)
            new_password = data.get('new_password')
            user.set_password(new_password)
            user.reset_password_token = None
            user.save()
        return Response({'success':True,'message':'Your password has been reset successfully. You can now log in with your new password.'},status=status.HTTP_200_OK)
    except:
        return Response({'error':"Error","message":'method not allowed'},status=status.HTTP_405_METHOD_NOT_ALLOWED)

@permission_classes([IsAuthenticated])
@api_view(['POST'])
def change_password(request):
    try:
        user=request.user
        data = json.loads(request.body)
        old_password = data.get('old_password')
        if user.check_password(old_password):
            new_password = data.get('new_password')
            
            # Set the new password (this hashes the password before saving)
            user.set_password(new_password)
            user.save()
            return Response({'success':True,'message':'your password has been changed'},status=status.HTTP_200_OK)
        
        else:
            return Response({'error':"Error","message":'Invalid password'},status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        return Response({'error':"Error","message":f'Internal server error {str(e)}'},status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetallAddresses(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        user = request.user
        try:
              all_addresses = Address.objects.filter(user=user.id)
              try :
                  user = CustomUser.objects.get(id=user.id)
              except CustomUser.DoesNotExist :
                  user = None

              if all_addresses.count() > 0 :
                  serializer = AddressSerializer(all_addresses, many=True)
                  data = {'success':True,'address':serializer.data}
                  if user:
                      data["username"] = user.username
                      data["user email"] = user.email
                      data["phone number"] = user.phone_number

                  return Response(data,status=status.HTTP_200_OK)
              else: 
                  data = {'success':False,"message":'No Addresses were found'}
                  return Response(data,status=status.HTTP_200_OK)
              
        except Exception as e:
            data = {'error':"Error","message":f"Internal Server Error: {str(e)}"}
            return Response(data,status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        # else:
        #     data = {'error':"Error","message":'Authentication Failed'}
        #     return Response(data,status=status.HTTP_400_BAD_REQUEST)
        

class Addresses(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
      # Get the address_id 
      address_id = request.GET.get('address_id')
      if not address_id : # Check address id is provided or ot
          return Response({'error':"Error","message":'Address id is not provided'},status=status.HTTP_400_BAD_REQUEST)
      
      # Check address is exits
      try:
          address =  Address.objects.get(id=address_id)
          serializer = AddressSerializer(address)
          return Response({'success':True,'address':serializer.data},status=status.HTTP_200_OK)
      except Address.DoesNotExist:
          data = {'error':"Error","message":'Address does not exist'}
          return Response(data,status=status.HTTP_404_NOT_FOUND)
            
    def post(self,request):
        if request.method == 'POST': # Check method
            user = request.user
            
            address_count = Address.objects.filter(user=user).count() # Find the provided user total address 
            # Max limit of address is 5
            if address_count >= 5:
                data = {'error':"Error","message":'You can add upto 5 addresses'}
                return Response(data,status=status.HTTP_404_NOT_FOUND)
            # get all the details or fields
            data = json.loads(request.body)
            address = data.get('address')
            city = data.get('city')
            state = data.get('state')
            country = data.get('country')
            pincode = data.get('pincode')

            # Now create a new address object
            if not address  or not city or not state or not pincode :
                data = {'error':"Error","message":"Please Provide all details"}
                return Response(data,status=status.HTTP_400_BAD_REQUEST)

            new_address = Address(user=user,address=address,city=city,state=state,country=country,pincode=pincode)
            # Save the new address to the object
            new_address.save()
            serializer = AddressSerializer(new_address)
            data = {'success':True,"message":'New Address Added Successfully','address':serializer.data}
            return Response(data,status=status.HTTP_200_OK)

        else: # Method not allowed
            data = {'error':"Error","message":"Method Not Allowed"}
            return Response(data,status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def put(self,request):
        if request.method == 'PUT':
            try:
              # Get address from address id
              address_id = request.GET.get('address_id')

              if not address_id:
                  return Response({'error':"Error","message":'Address not found'},status=status.HTTP_404_NOT_FOUND)
              
              try:
                  address = Address.objects.get(id=address_id) # Get address from address id
              except Address.DoesNotExist:
                  return Response({'error':"Error","message":'Address Does not exits'},status=status.HTTP_404_NOT_FOUND)
              
              # Get address update data from request body
              data = json.loads(request.body)
              # Update the address if it found
              if data.get('address') is not None and data.get('address') != "null":
                  address.address = data.get('address') #If address is not null then set the address
              if data.get('city') is not None and data.get('city') != "null":
                  address.city = data.get('city') #If city is not null then set the city
              if data.get('country') is not None and data.get('country') != "null":
                  address.country = data.get('country') #If city is not null then set the city
              if data.get('state') is not None and data.get('state') != "null":
                  address.state = data.get('state') #If state is not then set the state
              if data.get('pincode') is not None and data.get('pincode') != "null":
                  address.pincode = data.get('pincode') #If pincode is not null then set the pincode
              address.save() # Save the new updated address
              data = {'success':True,"message":"Address updated successfully"} # Send success
              return Response(data,status=status.HTTP_200_OK)
            except Exception as e:
                return Response({'error':"Error","message":f"Internal Server Error:- {str(e)}"},status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        
    def delete(self,request):
        try:
          address_id = request.GET.get('address_id')
          user_id = request.user.id
          try:
              address = Address.objects.get(id=address_id)
              if user_id == address.user.id: # Check user id and address user id is same or not
                  address.delete() # if same then delete the address
                  data = {'success':True,"message":"Address Delete Successfully"}
                  return Response(data,status=status.HTTP_200_OK)
              else:
                  return Response({'error':"Error","message":"Authentication Failed"},status=status.HTTP_400_BAD_REQUEST)
          except Address.DoesNotExist:
              data = {'error':"Error","message":"Address does not exist"}
              return Response(data,status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            data = {'error':"Error","message":'Authentication Error'}
            return Response(data,status=status.HTTP_400_BAD_REQUEST)
          
@permission_classes([IsAuthenticated])
@api_view(["POST"])
def verify_profile_otp(request):
        data = request.data
        otp = data.get('otp','')
        user_id=request.user.id
        updated_data = data.get('data',{})
        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return Response({'error':'Error','message':'User does not exist'},status=status.HTTP_400_BAD_REQUEST)

        try:
            otpObj = Otp.objects.get(user=user)
            if hash_otp(str(otp)) != otpObj.otp or not otpObj.is_valid:
                return Response({'error':'Error','message':"Invalid or expired OTP"})
            
            for key, value in updated_data.items():
                if key == "data" and isinstance(value, dict):  # Extract nested data
                    for sub_key, sub_value in value.items():
                        if hasattr(user, sub_key):
                            setattr(user, sub_key, sub_value)
                        else:
                            print(f"Skipping invalid field: {sub_key}")
                elif hasattr(user, key):
                    setattr(user, key, value)
                else:
                    print(f"Skipping invalid field: {key}")

            user.is_active = True
            user.save(update_fields=["email", "name", "phone_number", "username"])  # Ensure updates
            user.refresh_from_db() 
            # user.is_active = True
            # user.save()

            return Response({
                'success':True,
                'message':'Profile updated successfully',
                'updated_data':updated_data,
            },status=status.HTTP_200_OK)
        
        except Otp.DoesNotExist:
            return Response({'error':'Error','message':'User does not exist'},status=status.HTTP_400_BAD_REQUEST)


class UserProfile(APIView):
        permission_classes=[IsAuthenticated]
        
        def get(self,request):
          user_id = request.user.id
          try:
              user = CustomUser.objects.get(id=user_id)
          except:
              user = None
          
          if user is None:
              data = {'error':"Error","message":"User not found"}
              return Response(data,status=status.HTTP_404_NOT_FOUND)
          
          if not user.name:
              user.name = ''

          if not user.username:
              user.username = ''

          if not user.email:
              user.email = ''

          data = {
              "success":True,
              "phone_number":str( user.phone_number),
              "email":str(user.email),
              "username":str(user.username),
              "name":str(user.name),
          }
          return Response(data ,status=status.HTTP_200_OK)
        

        def put(self,request):
          user_id = request.user.id
          try:
              user = CustomUser.objects.get(id=user_id)
          except:
              user = None

          if user is None:
              data = {'error':"Error","message":"User not found"}
              return Response(data,status=status.HTTP_404_NOT_FOUND)
          data = json.loads(request.body)
          # Check for valid email and update
          email = data.get('email')
          updated = False
          if email:
              email_exists = CustomUser.objects.filter(email=email).exclude(id=user.id).exists()
              if not email_exists:
                  user.email = email
                  updated = True
              else:
                  return Response({'error':"Error","message":"User with this email already exists!"},status=status.HTTP_400_BAD_REQUEST)
              
          phone_number = data.get('phone_number')
          if phone_number:
              phone_number_exists = CustomUser.objects.filter(phone_number=phone_number).exclude(id=user.id).exists()
              if not phone_number_exists:
                  user.phone_number = phone_number
                  updated = True
              else:
                  return Response({'error':"Error","message":"User with this Phone Number already exists!"},status=status.HTTP_400_BAD_REQUEST)
              
          
          # Check for valid username and update
          name = data.get('name')
          username = data.get('username')
          if username:
              user.username = username
          if updated:
              user.is_active = False
              otp = str(random.randint(100000,999999))
              otpObj ,created = Otp.objects.get_or_create(user=user, defaults={'otp':hash_otp(otp)})
              otpObj.otp = hash_otp(otp)
              otpObj.save()
              html_content = f"""
              <html lang="en">
              <head>
              <meta name="viewport" content="width=device-width, initial-scale=1.0">
              <title>{OTP_HEADER}</title>
              <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css" rel="stylesheet">
              </head>
              <body style="font-family: 'Arial', sans-serif; background-color: #f7f7f7; margin: 0; padding: 0;">
              <div style="max-width: 600px; background-color: #fff; margin: 40px auto; padding: 3vw; border-radius: 2vw; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);">
              <!-- Header -->
              <div style="background-color: #FFFBF3; border-radius: 2vw 2vw 0 0; text-align: center; padding: 20px;">
              <img src="https://www.iconperfumes.in/_next/image/?url=%2Ficon_images%2Flogo.png&w=256&q=75" style="height:51px; width:132px; object-fit: contain;" alt="Logo" />
              </div>
              <!-- Content -->
              <div style="text-align: center;">
              <h2 style="font-size: 24px; color: #333; margin-bottom: 20px;">
              <i class="fas fa-check-circle" style="color: #FFFBF3; margin-right: 10px;"></i>Please Verify Email
              </h2>
              <p style="font-size: 16px; line-height: 1.5; color: #666;">Please enter this confirmation code to complete your account setup:</p>
              <div style="padding: 20px; background-color: #f1f1f1; border-radius: 10px; margin-bottom: 20px; font-size: 36px; font-weight: bold; color: #333; text-align: center;">{otp}</div>
              <p style="font-size: 16px; line-height: 1.5; color: #666; border-bottom: 1px dashed #666; padding-top: 20px; padding-bottom: 20px;">
              If you didn't request this, please ignore this message.
              </p>
              </div>
              <!-- Footer -->
              <div style="font-size: 12px; color: #888; text-align: center;">
              <p>You have received this notification because you update Your Profile.</p>
              <p></i>&copy; {current_year} Icon Perfumes. All rights reserved.</p>
              </div>
              </div>

              <style>
              @media (max-width: 600px) {{
              .container {{
              margin: 20px;
              }}
              .header, .content, .footer {{
              text-align: left;
              }}
              }}
              @media (max-width: 499px) {{
              div {{
              padding: 4vw;
              margin: 20px;
              border-radius: 3vw;
              }}
              .logo {{
              font-size: 20px;
              }}
              .cta-button {{
              padding: 8px 16px;
              font-size: 12px;
              }}
              .content h2 {{
              font-size: 20px;
              }}
              .otp-box {{
              font-size: 30px;
              padding: 15px;
              }}
              .confirm-button {{
              padding: 10px 20px;
              font-size: 14px;
              }}
              .footer {{
              font-size: 11px;
              }}
              }}
              </style>
              </body>
              </html>
              """
              send_mail(
                  subject=OTP_SUBJECT,
                  message="",
                  html_message=html_content,
                  from_email=settings.DEFAULT_FROM_EMAIL,
                  recipient_list=[email],
              )
              updated_data = {
                  'name':name,
                  'username':username,
                  'email':email,
                  'phone_number':phone_number,
              }
              data = {'success':True,"message":"Please verify your email to update your profile.",'masked_email':get_masked_email(email)}
              return Response(data,status=status.HTTP_200_OK)    
          else:
              return Response({'error':"Error","message":"Something went wrong"},status=status.HTTP_400_BAD_REQUEST)
            
        def delete(self,request):
            try:
                user=request.user
                if user is not None:
                    user.delete()
                    return Response({'success':True,'message':'User deleted successfully'},status=status.HTTP_200_OK)
            except:
                return Response({'error':"Error","message":"Authentication failed"},status=status.HTTP_400_BAD_REQUEST)
            

@permission_classes([IsAuthenticated])
@api_view(["GET"])
def getUser(request):
    try:
        user_id=request.user.id
        user = CustomUser.objects.get(id=user_id)
        user_data = CustomUserSerializer(user).data
        return Response({"success":True,"user":user_data,"is_staff":user.is_staff,'is_superuser':user.is_superuser},status=status.HTTP_200_OK)
            
    except CustomUser.DoesNotExist:
        return Response({"error":"User not found","message":"User does not exist"},status=status.HTTP_404_NOT_FOUND)
    
    except Exception as e:
        return Response({'error':"Error","message":f"Internal Server error: {str(e)}"},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@permission_classes([IsAuthenticated])
@api_view(["GET"])
def getUserById(request):
    try:
        id = request.GET.get("id")
        user = CustomUser.objects.get(id=id)
        user_data = CustomUserSerializer(user).data
        return Response({"success":True,"user":user_data,"is_staff":user.is_staff},status=status.HTTP_200_OK)
    
    except CustomUser.DoesNotExist:
        return Response({"error":"User not found","message":"User does not exist"},status=status.HTTP_404_NOT_FOUND)
    
    except Exception as e:
        return Response({'error':"Error","message":f"Internal Server error: {str(e)}"},status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@permission_classes([IsAuthenticated])
@api_view(["GET"])
def getAllUsers(request):
    try:
      user_id=request.user.i
      user = CustomUser.objects.get(id=user_id)
      if not user.is_staff:
          return Response({"error":"You are not authorized to access this endpoint","message":"You are not authorized to access this endpoint"},status=status.HTTP_403_FORBIDDEN)
      users = CustomUser.objects.all()
      users_data = CustomUserSerializer(users,many=True).data
      return Response({"success":True,"users":users_data},status=status.HTTP_200_OK)
            
    except CustomUser.DoesNotExist:
        return Response({"error":"User not found","message":"User does not exist"},status=status.HTTP_404_NOT_FOUND)
    
    except Exception as e:
        return Response({'error':"Error","message":f"Internal Server error: {str(e)}"},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@permission_classes([IsAuthenticated])
@api_view(["GET"])
def logout_account(request):
    is_localhost = bool(settings.DEBUG)
    response = JsonResponse({'success':True, 'message':"Logged out Successfully"})
    response.delete_cookie(
        key='token',
        domain=None if is_localhost is True else os.environ.get('DOMAIN')
        )

    return response