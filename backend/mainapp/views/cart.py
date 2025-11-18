from rest_framework.decorators import api_view , APIView, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from accounts.utils import append_log
from accounts.models import *
from mainapp.serializers import *
from mainapp.models import *



class UserCart(APIView):
    permission_classes = [IsAuthenticated]
    """ This function takes user token from query params and return and user cart with username and products. """
    def get(self, request):
        # first get user token cause authorize user only can access cart
        user = request.user
        try:
            cart_items = Cart.objects.filter(user=user)
            if not cart_items.exists():
                return Response({'success':True,'message':'No Items in cart', 'cart_items': []},status=status.HTTP_200_OK)

            serializer = CartSerializer(cart_items,many=True)
            cart_serialized = serializer.data

            return Response({'success':True,'cart_items':cart_serialized},status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error":'Error','message':f'Internal server error:-{str(e)}'},status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self,request,id):
        """ This function takes token in query params and product id in url and add product into cart."""
        quantity = request.query_params.get('quantity')
        user = request.user        
        if not quantity:
            quantity = 1
        try:
            try:
                variant = ProductVariant.objects.get(id=id)
            except ProductVariant.DoesNotExist:
                return Response({'success':False,'message':'This variant does not exist'},status=status.HTTP_400_BAD_REQUEST)
            
            cart = Cart.objects.filter(variant=variant, user=user)
            if cart.exists():
                return Response({'success':True,'message':'Item already exists in cart'},status=status.HTTP_400_BAD_REQUEST)
            
            cart = Cart.objects.create(user=user, variant=variant,quantity=quantity)
            serializer = CartSerializer(cart)
            
            return Response({'success': True,'message': "Product Added To Cart Succesfully", 'cart': serializer.data},status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error":'Error','message':f"Internal Server Error:- {str(e)}"},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def delete(self,request,id):
        """ This function takes token in query params and product id in url parameter and delete the product from the user cart."""
        user = request.user
        try:
            try:
                variant = ProductVariant.objects.get(id=id)
            except ProductVariant.DoesNotExist:
                return Response({'error':'Error','message':'Product does not exist'},status=status.HTTP_404_NOT_FOUND)
            
            try:
                cart = Cart.objects.get(user=user, variant=variant)
                cart.delete()
                return Response({'success':True,'message':'Item Removed From Cart successfully'},status=status.HTTP_200_OK)
            except Cart.DoesNotExist:
                return Response({"error":'Error','message':'Product is not exists in cart'},status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({"error":'Error','message':f"Internal Server Error:- {str(e)}"},status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@permission_classes([IsAuthenticated])
@api_view(['POST'])
def plus_cart(request,id):
    quantity = request.query_params.get('quantity')
    user = request.user
    try:
        quantity = int(quantity) if quantity else 1
    except ValueError:
        quantity = 1
    try:
        try:
            variant = ProductVariant.objects.get(id=id)
        except ProductVariant.DoesNotExist:
            return Response({'error':'Error',"message":'Variant does not exist'},status=status.HTTP_400_BAD_REQUEST)
        try:
            cart = Cart.objects.get(user=user,variant=variant)
            if (cart.quantity + 1) >= cart.variant.stock:
                return Response({'success': False, 'message':f'Currently Only {cart.variant.stock} Quantity is Available for {cart.variant.product.title[:12]} {"..." if len(cart.variant.product.title) > 12 else ""}'})
            cart.quantity += quantity
            cart.save()
            return Response({'success': True,'message':'Quantity updated successfully'},status=status.HTTP_200_OK)
        
        except Cart.DoesNotExist:
            return Response({'error':'Error','message':'Product does not exist in cart'},status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        return Response({'error':"Error",'message':f'Internal Server Error:- {str(e)}'},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
      
@permission_classes([IsAuthenticated])
@api_view(['POST'])
def minus_cart(request,id):
    user = request.user
    try:
        try: 
            variant = ProductVariant.objects.get(id=id)
        except ProductVariant.DoesNotExist:
            return Response({'error':'Error',"message":'Product does not exist'},status=status.HTTP_404_NOT_FOUND)

        try:
            cart = Cart.objects.get(user=user,variant=variant)
            if cart.quantity > 1 :
                cart.quantity -= 1
                cart.save()
                return Response({'success': True,'message':'Quantity Updated Successfully'},status=status.HTTP_200_OK)
            else:
                return Response({'success':False,'message':'Do you want to remove product from cart?'},status=status.HTTP_406_NOT_ACCEPTABLE)
        except  Cart.DoesNotExist:
            return Response({'error':'Error','message':'Product Does not exists in cart'},status=status.HTTP_404_NOT_FOUND)    
    except Exception as e:
        return Response({'error':'Error','message':f"Internal Server Error:- {str(e)}"},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    