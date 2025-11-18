from django.shortcuts import get_object_or_404
from django.http import JsonResponse

from rest_framework.decorators import api_view , APIView, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from accounts.utils import append_log
from accounts.models import *
from mainapp.serializers import *
from mainapp.models import *

class UserOrders(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        user = request.user
        try:
            # get the orders for user that requested
            orders = Order.objects.filter(user=user)
            if orders.exists():
                serializer = OrderSerializer(orders,many=True)
                orders_serialized = serializer.data
                
                return Response({'success':True,'orders':serializer.data},status=status.HTTP_200_OK)
            else:
                return Response({'success': True, 'message': 'No orders found', 'orders':[]}, status=status.HTTP_404_NOT_FOUND)

        # if some error found then send internal server error
        except Exception as e:
            return Response({'success':False,'message':f"Internal Server Error: {str(e)}"},status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self,request,id):
        try:
            user = request.user
            # now find the order for requested user
            order = get_object_or_404(Order,id=id,user=user)
            # if order found then delete it 
            order.delete()
            return Response({'success':True,'message':'Order deleted successfully'},status=status.HTTP_200_OK)
        
        except Order.DoesNotExist: # if order not found then send error
            return Response({'error':'Error',"message":'Order does not exist'},status=status.HTTP_400_BAD_REQUEST)
        
        # if some error then send internal server error
        except Exception as e:
            return Response({'success':False,'message':f"Internal Server Error: {str(e)}"},status=status.HTTP_400_BAD_REQUEST)


@permission_classes([IsAuthenticated])
@api_view(["GET"])
def getOrder(request, order_id):
    try:
        user = request.user
        # get the orders for user that requested
        order = Order.objects.get(id=order_id)

        if order.user != user:
            return Response({'error':'Error',"message":'You are not allowed to view this information'},status=status.HTTP_400_BAD_REQUEST)
        if order:
            order_items = OrderItem.objects.filter(order=order.id)
            serializer = OrderItemSerializer(order_items,many=True)    
            order_serializer = OrderSerializer(order)
            order_serialized = order_serializer.data
            order_items_serialized = serializer.data    

            return Response({'success':True,'order_items':order_items_serialized,'order':order_serialized},status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Error', 'message': 'No orders found'}, status=status.HTTP_400_BAD_REQUEST)
                
    except Order.DoesNotExist:
        return Response({'error':'Error','message':'Order not found'},status=status.HTTP_400_BAD_REQUEST)

    # if some error found then send internal server error
    except Exception as e:
        return Response({'success':False,'message':f"Internal Server Error: {str(e)}"},status=status.HTTP_500_INTERNAL_SERVER_ERROR)




@permission_classes([IsAuthenticated])
@api_view(['POST'])
def re_order(request):
    try:
        data = request.data
        user = request.user
        order_id = data.get('order_id')
        order = get_object_or_404(Order, id=order_id)
        order_items = OrderItem.objects.filter(order=order)
        for item in order_items:
            Cart.objects.create(user=user, variant=item.variant, quantity=item.quantity)
        return Response({'success': True, 'message': 'Order items added to cart successfully'}, status=status.HTTP_200_OK)

    except Exception as e:
        print(e)
        return Response({"error":"Error","message":f"Internal Server Error :- {str(e)}"},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

@permission_classes([IsAuthenticated])
@api_view(["POST"])
def cancel_order(request,id):
    try:
        user = request.user
        order = get_object_or_404(Order,id=id,user=user)
        if order.order_status == 'PENDING':
            order.order_status = 'CANCELLED'
            order.save()
            return Response({'success':True,'message':'Order Cancelled Successfully'},status=status.HTTP_200_OK)
    except Order.DoesNotExist:
        return Response({'error':'Error','message':'Order not found'},status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        print(e)
        return Response({"error":"Error","message":f"Internal Server Error :- {str(e)}"},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    


# ============ NOTE: NOT IN USE =============
@permission_classes([IsAuthenticated])
@api_view(['POST'])
def return_order(request):
    try:
        user = request.user
        data = request.data
        order = get_object_or_404(Order,id=id,user=user)
        if order.order_status == 'Delivered':
            order.order_status = 'Returned'
            order.save()
            return Response({'success':True,'message':'Order Returned successfully'},status=status.HTTP_200_OK)
        else:
            return Response({'success':False,'message':'You can only return Delivered orders'},status=status.HTTP_200_OK)

    except Order.DoesNotExist:
        return Response({"error":"Error","message":"Order not found"},status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        print(e)
        return Response({"error":"Error","message":f"Internal Server Error :- {str(e)}"},status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def order_change(request):
    if request.method == "GET":
        id = request.GET["id"]
        order = Order.objects.get(id=id)
        if order.is_new == True:
            order.is_new = False
            order.save()
        return JsonResponse("success",safe=False)
    return JsonResponse("error",safe=False)

def order_check(request):
    if request.method == "GET":
        id = request.GET["id"]
        order = Order.objects.get(id=id)
        if order.is_new == True:        
            return JsonResponse("true",safe=False)
        elif order.is_new == False:
            return JsonResponse("false",safe=False)

    return JsonResponse("error",safe=False)