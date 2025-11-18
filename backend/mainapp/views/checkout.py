import json
import razorpay
import traceback
import hashlib

from datetime import datetime
from datetime import timedelta
from decimal import Decimal
from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view , permission_classes, APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status

from accounts.models import *
from mainapp.serializers import *
from mainapp.models import *
from mainapp.views.utils import *
from mainapp.views.shiprocket import *


class VerifyPaymentAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def _verify_payment(self, data):
        """Verify payment with PayU"""
        payu_key = settings.PAYU_MERCHANT_KEY
        payu_salt = settings.PAYU_MERCHANT_SALT
        payu_txnid = data.get("txnid")

        hash_str = f"{payu_key}|verify_payment|{payu_txnid}|{payu_salt}"
        hashh = hashlib.sha512(hash_str.encode('utf-8')).hexdigest().lower()

        payload = {
            "key": payu_key,
            "command": "verify_payment",
            "var1": payu_txnid,
            "hash": hashh
        }

        url = "https://info.payu.in/merchant/postservice?form=2"
        resp = requests.post(url, data=payload)
        return resp.json()
    
    def post(self, request):
        try:
            data = request.data
            payu_txnid = data.get("txnid")
            
            # Verify payment
            response = self._verify_payment(data)
            if response.get('status') != 1:
                return Response({"success": False, "message": "Payment failed ❌"}, status=400)
            
            # Find transaction and order
            transaction = Transaction.objects.filter(transaction_id=payu_txnid).first()
            if not transaction:
                return Response({
                    'success': False,
                    'message': 'Transaction not found',
                    'data': []
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if order already processed
            if transaction.order.payment_status == "Paid":
                return Response({
                    'success': False,
                    'message': 'Order already processed',
                    'order_id': transaction.order.id
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Update order and transaction status
            transaction.order.payment_status = "Paid"
            transaction.order.save()
            
            transaction.transaction_status = "Paid"
            transaction.save()
            
            # Generate invoice
            generate_invoice(transaction.order.email, transaction.order.order_number)
            
            return Response({
                'success': True,
                'message': 'Payment verified successfully',
                'order_id': transaction.order.id
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            traceback.print_exc()
            return Response({
                'error': 'Error',
                'message': f"Internal server error: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
@permission_classes([AllowAny])
@api_view(['POST'])
def calculate_checkout_total(request):
    try:
        data = json.loads(request.body)
        source = data.get('source')
        promo_code = data.get('promo_code', '').strip()
        vat_rate = 0
        original_price = 0
        discount_amount = 0
        user = request.user
        pickup_postcode = settings.PICKUP_POSTCODE
        pincode = data.get("pincode")
        payment_method = data.get("paymentMethod")
        shipping_charge=0
        shiprocket_info={}
        cod = 0 if payment_method=="ONLINE" else 1
        
        if pincode:
            if data.get('source') == 'cart':
                variants = [
                {
                    'variant': item.get('variant', {}),
                    'quantity': item.get('quantity', 1)
                }
                for item in data.get('cart_data', [])
                ]
            else:
                variants = [
                    {'variant':data.get('cart_data',[]).get('item'),'quantity':data.get('cart_data',[]).get('quantity')}
                    ]
           
            shiprocket_info = get_minimum_courier_rate(pickup_postcode, pincode, cod, variants)
            if shiprocket_info is None:
                shiprocket_info = {"company_rate": 45}

            shipping_charge = 45
        # Calculate original price based on source
        outof_stock_products = []
        if source == 'cart':
            cart_data = data.get('cart_data')
            if not cart_data:
                return Response({'error': 'Error', 'message': 'Cart data not found'}, status=status.HTTP_400_BAD_REQUEST)
            
            cart_items = []
            for item in cart_data:
                variant = ProductVariant.objects.get(id=item['variant']['id'])
                quantity = item['quantity']
                cart_items.append({'variant': variant, 'quantity': quantity})
                if variant.stock < int(quantity):
                    title = variant.product.title
                    short_title = (title[:12] + '...') if len(title) > 12 else title 
                    outof_stock_products.append(short_title)
            
            original_price = sum(item['variant'].discounted_price * item['quantity'] for item in cart_items)
        else:
            variant_id = data['cart_data']['item']['id']
            quantity = data['cart_data']['quantity']
            product_variant = ProductVariant.objects.get(id=variant_id)
            original_price = product_variant.discounted_price * int(quantity)
            if product_variant.stock < int(quantity):
                title = product_variant.product.title
                short_title = (title[:12] + '...') if len(title) > 12 else title 
                outof_stock_products.append(short_title)

        subtotal = original_price / Decimal(1 + vat_rate)

        if len(outof_stock_products) > 0:
            return Response({
                'success':False, 
                'message':f"Sorry following product(s) are currently unavailable {' ,'.join(outof_stock_products)}",
                'amount': {
                    'original_price': 0,
                    'shipping':{},
                    'sub_total': 0,
                    'tax': 0,
                    'tax_rate': 0,
                    'discount': 0,
                    'total': 0,
                }
            },status=status.HTTP_409_CONFLICT)
        
        if promo_code:
            try:
                promo = check_promo_code(promo_code)
                discount_type = promo.get('type', '')

                if discount_type == 'promotion':
                    promotion = Promotion.objects.get(coupon_code=promo_code, is_active=True)
                    if not promotion.is_valid():
                        return Response({'error': 'Error', 'message': 'Invalid or expired promo code'}, status=status.HTTP_400_BAD_REQUEST)

                    # Check for WELCOME10 restriction
                    if promotion.coupon_code == 'WELCOME10' and user and Order.objects.filter(user=user).exists():
                        return Response({'error': 'Error', 'message': 'This coupon is valid only on first order'}, status=status.HTTP_400_BAD_REQUEST)

                    if source == 'cart' and promotion.promotion_type == 'cart':
                        discount_amount = promotion.discount_value if promotion.discount_type == 'amount' else original_price * (promotion.discount_value / 100)
                    elif promotion.promotion_type == 'product':
                        if source == 'cart':
                            for item in cart_items: 
                                if item['variant'].id == promotion.product_variant.id:
                                    discount_amount = promotion.calculate_discount(item['variant'].discounted_price) * item['quantity']
                                    break
                            else:
                                return Response({'error': 'Error', 'message': 'Promo code is not valid for these products'}, status=status.HTTP_400_BAD_REQUEST)
                        elif promotion.product_variant.id == variant_id:
                            discount_amount = promotion.discount_value if promotion.discount_type == 'fixed' else original_price * (promotion.discount_value / 100)
                        else:
                            return Response({'error': 'Error', 'message': 'Promo code is not valid for this product'}, status=status.HTTP_400_BAD_REQUEST)
                    else:
                        return Response({'error': 'Error', 'message': 'Promo code is not valid for this purchase type'}, status=status.HTTP_400_BAD_REQUEST)


                else:
                    return Response({'error': 'Error', 'message': 'Invalid promo code'}, status=status.HTTP_400_BAD_REQUEST)

                # Ensure discount doesn't exceed original price
                discount_amount = min(discount_amount, original_price)

                # Recalculate with discount
                discounted_price = original_price - Decimal(discount_amount)
                subtotal = discounted_price / Decimal(1 + vat_rate)
            except (Promotion.DoesNotExis):
                return Response({'error': 'Error', 'message': 'Invalid promo code'}, status=status.HTTP_400_BAD_REQUEST)

        # Calculate final amounts
        vat_amount = original_price - subtotal
        total_ex_ship = float(original_price) - float(discount_amount)
        if total_ex_ship >= 500:
            shipping_charge = 0
            shiprocket_info['company_rate'] = 0
        else:
            shipping_charge = 45
            shiprocket_info['company_rate'] = 45
        
        if request.user.id in [6,1,14]:
            shipping_charge = 0
            shiprocket_info['company_rate'] = 0

        total_amount = float(original_price) + float(shipping_charge) - float(discount_amount)
        # Prepare response 
        response_data = {
            'success': True,
            'amount': {
                'original_price': "{:.2f}".format(original_price),
                'shipping':shiprocket_info,
                'sub_total': "{:.2f}".format(subtotal),
                'tax': "{:.2f}".format(vat_amount),
                'tax_rate': round(vat_rate * 100),
                'discount': "{:.2f}".format(discount_amount),
                'total': "{:.2f}".format(total_amount),
            }
        }

        if promo_code and discount_amount > 0:
            response_data['discount_type'] = discount_type
            response_data['message'] = f"{'Promo code'} applied successfully! You saved ₹{discount_amount:.2f}"

        return Response(response_data, status=status.HTTP_200_OK)

    except ProductVariant.DoesNotExist:
        return Response({'error': 'Error', 'message': 'Product variant not found'}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        traceback.print_exc()
        return Response({'error': 'Error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class PaymentOrderAPIView(APIView):
    permission_classes=[IsAuthenticated]

    def _create_transaction_id(self):
        """Generate a unique transaction ID"""
        return 'ICP' + str(generate_transaction_id())

    def _create_order_number(self, user, order_id):
        """Generate order number based on user and timestamp"""
        now = datetime.now()
        return f"ICP{user.id}{now.day}{now.month}{now.year}{order_id}"

    def _process_promo_code(self, discount_obj, discount_amount):
        """Process and validate promo code"""
        if not discount_obj or discount_amount == "0.00":
            return None

        discount_code = dict(discount_obj).get('code')
        promo = check_promo_code(discount_code)
        discount_type = promo.get('type', '')

        if not discount_type or not (discount_type == "promotion" and discount_obj.get('type', '') == "promotion"):
            return None

        try:
            promotion = Promotion.objects.get(coupon_code=discount_code, is_active=True)
            return promotion
        except Promotion.DoesNotExist:
            return None

    def _create_order(self, user, data, payment_method, source):
        """Create order based on source (buynow or cart)"""
        promotion = self._process_promo_code(data.get('promo'), data.get('amount', {}).get('discount', "0.00"))
        transaction_id = self._create_transaction_id()
        
        if source == 'buynow':
            return self._create_buynow_order(user, data, payment_method, promotion, transaction_id)
        elif source == 'cart':
            return self._create_cart_order(user, data, payment_method, promotion, transaction_id)
        else:
            return None, "Invalid source"

    def _create_buynow_order(self, user, data, payment_method, promotion, transaction_id):
        """Create order for buynow flow"""
        variant = get_object_or_404(ProductVariant, id=data['product']['item'].get('id'))
        quantity = data['product'].get('quantity')
        
        # Calculate prices
        original_price = variant.discounted_price * quantity
        discount = Decimal(str(data.get('amount', {}).get('discount', 0)))
        discounted_price = original_price - discount
        
        shipping_obj = data.get('shipping', {})
        shipping_price = Decimal('0') if discounted_price >= Decimal('500') else Decimal(str(shipping_obj.get('company_rate', 0)))
        
        final_price = discounted_price + shipping_price
        
        # Create order
        order = Order.objects.create(
            user=user,
            name=data.get('name'),
            address=data.get('address'),
            city=data.get('city'),
            state=data.get('state'),
            country=data.get('country'),
            pincode=data.get('pincode'),
            sub_total=discounted_price,
            discount=discount,
            gst=0,
            courier_company_id=shipping_obj.get('company_id'),
            courier_company=shipping_obj.get('company_name'),
            shipping_charges=shipping_price,
            final_price=final_price,
            transaction_id=transaction_id,
            payment_status="Pending",  # Will be updated after payment verification
            payment_method=payment_method,
            email=data.get('email'),
            phone_number=data.get('phone')
        )
        
        # Create order item
        price = variant.discounted_price * Decimal(quantity)
        order_item = OrderItem.objects.create(
            order=order,
            variant=variant,
            quantity=quantity,
            price=price,
            final_price=price
        )
        
        # Apply promotion if applicable
        if promotion and promotion.promotion_type == "product" and promotion.product_variant == variant:
            item_discount = promotion.calculate_discount(price)
            order_item.discount = item_discount
            order_item.final_price = price - item_discount
            order_item.promotion = promotion
            order_item.save()
        
        return order, None

    def _create_cart_order(self, user, data, payment_method, promotion, transaction_id):
        """Create order for cart flow"""
        cart_items = Cart.objects.filter(user=user)
        for item in cart_items:
            if not item.variant.stock or item.variant.stock < item.quantity:
                return None, f'{item.variant} is out of stock'

        # Calculate prices
        original_price = sum((item.variant.discounted_price * item.quantity for item in cart_items))
        discount = Decimal(str(data.get('amount', {}).get('discount', 0)))
        discounted_price = original_price - discount
        
        shipping_obj = data.get('shipping', {})
        shipping_price = Decimal('0') if discounted_price >= Decimal('500') else Decimal(str(shipping_obj.get('company_rate', 0)))
        
        final_price = discounted_price + shipping_price
        
        # Create order
        order = Order.objects.create(
            user=user,
            name=data.get('name'),
            address=data.get('address'),
            city=data.get('city'),
            state=data.get('state'),
            country=data.get('country'),
            pincode=data.get('pincode'),
            sub_total=discounted_price,
            discount=discount,
            gst=0,
            courier_company_id=shipping_obj.get('company_id'),
            courier_company=shipping_obj.get('company_name'),
            shipping_charges=shipping_price,
            final_price=final_price,
            transaction_id=transaction_id,
            payment_status="Pending",  # Will be updated after payment verification
            payment_method="Prepaid" if payment_method == "ONLINE" else "COD",
            email=data.get('email'),
            phone_number=data.get('phone')
        )
        
        # Create order items
        for item in cart_items:
            price = item.variant.discounted_price * Decimal(item.quantity)
            order_item = OrderItem.objects.create(
                order=order,
                variant=item.variant,
                quantity=item.quantity,
                price=price,
                final_price=price
            )
            
            # Apply promotion if applicable
            if promotion and promotion.promotion_type == "cart":
                proportion = (item.variant.discounted_price * Decimal(item.quantity)) / (order.sub_total + discount)
                item_discount = discount * proportion
                order_item.discount = item_discount
                order_item.final_price = price - item_discount
                order_item.promotion = promotion
                order_item.save()
        
        return order, None
    def _save_address(self, user, data):
        addresses = Address.objects.filter(user=user)
        address = data.get('address')
        if addresses.count() < 5 and not Address.objects.filter(address=address).exists():
            Address.objects.create(
                user=user,
                address=address,
                city=data.get("city"),
                country=data.get("country"),
                state=data.get("state"),
                pincode=data.get("pincode"),
                default=False
            )

    def post(self, request):
        try:
            user = request.user
            data = request.data
            source = request.query_params.get('source')
            payment_method = data.get('paymentMethod', 'COD')

            # First create order
            order, error = self._create_order(user, data, payment_method, source)
            if error:
                return Response({'error': 'Error', 'message': error}, status=status.HTTP_400_BAD_REQUEST)
            
            # Generate order number
            order_number = self._create_order_number(user, order.id)
            order.order_number = order_number
            order.save()

            self._save_address(user, data)

            # Note: Currently NOT in use
            # if payment_method == "COD":
            #     # Generate invoice
            #     generate_invoice(order.email, order_number)
                
            #     # Clear cart if this was a cart order
            #     if source == 'cart':
            #         Cart.objects.filter(user=user).delete()
                
            #     return Response({
            #         'success': True,
            #         'message': 'Order created successfully',
            #         'order_id': order.id
            #     }, status=status.HTTP_201_CREATED)
            
            # For online payment, create payment request
            key = settings.PAYU_MERCHANT_KEY
            salt = settings.PAYU_MERCHANT_SALT
            payu_base_url = settings.PAYU_BASE_URL
            
            # Create hash for payment
            hash_str = f"{key}|{order.transaction_id}|{order.final_price}|Order Payment|{order.name}|{order.email}|||||||||||{salt}"
            hashh = hashlib.sha512(hash_str.encode('utf-8')).hexdigest().lower()
            
            # Create transaction record
            transaction = Transaction.objects.create(
                user=user,
                name=order.name,
                amount=str(order.final_price),
                transaction_id=order.transaction_id,
                phone_number=order.phone_number,
                token=hashh,
                order=order
            )
            
            # Prepare payment payload
            payu_payload = {
                "key": key,
                "txnid": order.transaction_id,
                "amount": str(order.final_price),
                "productinfo": "Order Payment",
                "firstname": order.name,
                "email": order.email,
                "phone": order.phone_number,
                "surl": f"{settings.WEB_URL}{settings.PAYU_SUCCESS_URL}?txnid={order.transaction_id}&hash={hashh}&status=success",
                "furl": f"{settings.WEB_URL}{settings.PAYU_FAILURE_URL}?status=failed",
                "hash": hashh,
                "service_provider": "payu_paisa"
            }
            
            return Response({
                "success": True,
                "payu_url": payu_base_url,
                "params": payu_payload,
                "order_id": order.id
            }, status=status.HTTP_200_OK)
        
            # amount = request.data.get("amount")
            # txnid = "ICP" + generate_transaction_id()
            # productinfo = "Order Payment"
            # firstname = request.data.get("name") or user.name
            # email = user.email
            # # Get PayU credentials from settings
            # key = settings.PAYU_MERCHANT_KEY
            # salt = settings.PAYU_MERCHANT_SALT  # use exactly what PayU provides
            # payu_base_url = settings.PAYU_BASE_URL  # e.g., "https://secure.payu.in/_payment"

            # # Create the hash string
            # hash_str = f"{key}|{txnid}|{amount}|{productinfo}|{firstname}|{email}|||||||||||{salt}"
            # hashh = hashlib.sha512(hash_str.encode('utf-8')).hexdigest().lower()
            # transaction = Transaction.objects.create(
            #     user=user,
            #     name=user.name,
            #     amount=amount,
            #     transaction_id=txnid,
            #     phone_number=user.phone_number,
            #     token=hashh
            # )
            # transaction.save()
            # payu_payload = {
            #     "key": key,
            #     "txnid": txnid,
            #     "amount": amount,
            #     "productinfo": productinfo,
            #     "firstname": firstname,
            #     "email": email,
            #     "phone": user.phone_number,
            #     "surl": f"{settings.WEB_URL}{settings.PAYU_SUCCESS_URL}?txnid={txnid}&hash={hashh}&status=success",  # success callback
            #     "furl": f"{settings.WEB_URL}{settings.PAYU_FAILURE_URL}?status=failed",  # failure callback
            #     "hash": hashh,
            #     "service_provider": "payu_paisa"
            # }
            # return Response({
            #     "success":True,
            #     "payu_url": payu_base_url,
            #     "params": payu_payload
            # }, status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            return Response({"success":False, "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
