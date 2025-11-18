import math
import json

from rest_framework.decorators import APIView,permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from collections import Counter

from accounts.models import *
from mainapp.serializers import *
from mainapp.models import *


class UserReview(APIView):

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAuthenticated()]
    
    def get(self, request, product_slug):
        try:
            product = Product.objects.get(slug=product_slug)
            reviews = Review.objects.filter(product=product).order_by('-created_at')
            page = int(request.GET.get('page',1))
            limit = int(request.GET.get('limit',2))
            offset = page  * limit

            if not reviews.exists():
                return Response({'success':False, 'message':"Reviews Not Found"},status=status.HTTP_400_BAD_REQUEST)

            serializer = ReviewSerializer(reviews, many=True)

            avg = round(sum([review.rating for review in reviews]) / reviews.count(),1)
            
            all_ratings = reviews.values_list("rating",flat=True)
            counts = Counter(all_ratings)
            ratings = {str(i):counts.get(i,0) for i in range(1,6)}
            total_pages = math.ceil(len(reviews) / limit)
            all_reviews = serializer.data[:offset]

            return Response({'success':True, 'message':"Reviews Fetched Successfully", 'data':{'reviews':all_reviews,'page':page,'total_pages':total_pages,'total_reviews':len(all_reviews),'ratings':ratings,'average':avg}},status=status.HTTP_200_OK)
        except Product.DoesNotExist:
            return Response({'success':False, 'message':"Product Not Found"},status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({'success':False, 'message':f"Internal Server Error {str(e)}"},status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    
    def post(self,request,id):
        user = request.user
        try:        
            try:
                product = Product.objects.get(id=id)
            except Product.DoesNotExist: # if user cart does not exist send error
                return Response({'error':'Error',"message":'Product does not exist'},status=status.HTTP_400_BAD_REQUEST)

            # Check the number of reviews already submitted by this user for the product
            review_count = Review.objects.filter(user=user, product=product).count()
            if review_count >= 3:
                return Response({'error': 'Error', "message": 'You can only submit up to 3 reviews for this product.'}, status=status.HTTP_400_BAD_REQUEST)
            # Get review data from the request
            
            data = json.loads(request.body)
            if not data:
                return Response({'error': 'Error', "message": 'Please Provide Data Properly'}, status=status.HTTP_400_BAD_REQUEST)
            rating = data.get('rating')
            comment = data.get('comment')
            
            # Create a new review for the product
            review = Review.objects.create(
                user=user, 
                product=product, 
                rating=rating, 
                comment=comment
            )

            # Serialize the new review
            review_serializer = ReviewSerializer(review)

            return Response({
                "success": True,
                "message": "Review posted successfully",
                "review": review_serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({"error":'Error','message':f"Internal Server Error:- {str(e)}"},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
