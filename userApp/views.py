from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.core.mail import send_mail
from django.db.utils import IntegrityError
from .models import CustomUser
from django.contrib.auth.hashers import make_password
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .models import CustomUser

from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny
from rest_framework.authentication import BasicAuthentication
from django.contrib.auth.hashers import check_password
from django.shortcuts import get_object_or_404
import random
import string




import re
from django.core.mail import send_mail
from django.contrib.auth.hashers import make_password
from django.db import IntegrityError
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
# from validate_email_address import validate_email
from .models import CustomUser

def is_valid_password(password):
    """Validate password complexity."""
    if len(password) < 8:
        return "Password must be at least 8 characters long."
    if not any(char.isdigit() for char in password):
        return "Password must include at least one number."
    if not any(char.isupper() for char in password):
        return "Password must include at least one uppercase letter."
    if not any(char.islower() for char in password):
        return "Password must include at least one lowercase letter."
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return "Password must include at least one special character (!@#$%^&* etc.)."
    return None

def is_valid_email(email):
    """Validate email format and domain."""
    email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"

    # Check format
    if not re.match(email_regex, email):
        return "Invalid email format."



    #check if entered password has been used before
    if not email.endswith("@gmail.com"):
        return "Only Gmail addresses are allowed for registration."

    return None



def generate_secure_password():
    """Generate a secure random password that meets complexity requirements."""
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    special_chars = "!@#$%^&*(),.?\":{}|<>"
    
    # Ensure at least one of each required character type
    password = [
        random.choice(lowercase),
        random.choice(uppercase),
        random.choice(digits),
        random.choice(special_chars)
    ]
    
    # Fill remaining length with random characters from all types
    all_chars = lowercase + uppercase + digits + special_chars
    password.extend(random.choice(all_chars) for _ in range(4))  # 4 more chars to make it 8 total
    
    # Shuffle the password characters
    random.shuffle(password)
    return ''.join(password)

@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    phone_number = request.data.get('phone')
    email = request.data.get('email')
    role = request.data.get('role')
    is_admin_creating = request.data.get('is_admin_creating', False)
    password = None
    confirm_password = None
    
    if not is_admin_creating:
        password = request.data.get('password')
        confirm_password = request.data.get('confirmPassword')

    # Basic validations
    if not phone_number:
        return Response({"error": "Phone number is required."}, status=400)
    
    if not role:
        return Response({"error": "Role is required."}, status=400)

    # Check if the phone number already exists
    if CustomUser.objects.filter(phone_number=phone_number).exists():
        return Response({"error": "A user with this phone number already exists."}, status=400)

    # Validate email if provided
    if email:
        if CustomUser.objects.filter(email=email).exists():
            return Response({"error": "A user with this email already exists."}, status=400)
        email_error = is_valid_email(email)
        if email_error:
            return Response({"error": email_error}, status=400)

    try:
        if is_admin_creating:
            # Generate a secure random password for admin-created accounts
            password = generate_secure_password()
        else:
            password = request.data.get('password')
            confirm_password = request.data.get('confirmPassword')
            print(f"Password: {password}\n")
            print(f"Confirm Password: {confirm_password}\n")
            # Validate user-provided password
            if not password or not confirm_password:
                return Response({"error": "Password and confirm password are required."}, status=400)
            
            if password != confirm_password:
                return Response({"error": "Passwords do not match."}, status=400)
            
            password_error = is_valid_password(password)
            if password_error:
                return Response({"error": password_error}, status=400)
            
            if role not in ['farmer', 'buyer']:
                return Response({"error": "Can not create this user"}, status=400)

        # Hash the password
        hashed_password = make_password(password)

        # Create the user
        user = CustomUser.objects.create_user(
            phone_number=phone_number,
            email=email,
            role=role,
            password=password
        )

        # Send the password to the user's email if email is provided
        if email:
            message = (
                "Hello,\n\nYour account has been created in Smart Sunflower Production and Marketing Integration System.\n"
                f"Your password is: {password}\n\n"
            )
            if is_admin_creating:
                message += "If you did not register by your-self then this password is a system-generated password. \nPlease change it after your first login.\n"

            
            send_mail(
                subject="Your Account Password",
                message=message,
                from_email="no-reply@gmail.com",
                recipient_list=[email],
            )

        response_data = {"message": "User registered successfully."}
        if is_admin_creating and not email:
            # If admin is creating account without email, return the generated password
            response_data["generated_password"] = password
            response_data["warning"] = "Please securely share this password with the user."
            
        return Response(response_data, status=201)

    except IntegrityError:
        return Response({"error": "A user with this phone number already exists."}, status=400)




@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def login_user(request):
    email_or_phone = request.data.get('identifier')
    password = request.data.get('password')

    print(f"\n Submitted data: \n Email/Phone: {email_or_phone} \n Password: {password} \n")

    # Basic validations
    if not email_or_phone or not password:
        return Response({"error": "Email/Phone and password are required."}, status=400)

    print(f"\n Submitted data: \n Email/Phone: {email_or_phone} \n Password: {password} \n")

    try:
        # Check if user exists by email or phone
        user = CustomUser.objects.filter(email=email_or_phone).first() or CustomUser.objects.filter(phone_number=email_or_phone).first()

        if not user:
            print("No user found with this email or phone number\n")
            return Response({"error": "No user found with this email or phone."}, status=401)

        # Manually check password (since authenticate only works with USERNAME_FIELD)
        if not check_password(password, user.password):
            print("Invalid password \n")
            return Response({"error": "Invalid password."}, status=401)

        if not user.is_active:
            print("This account is inactive\n")
            return Response({"error": "This account is inactive."}, status=401)

        # Generate JWT token
        refresh = RefreshToken.for_user(user)

        return Response({
            "id": user.id,
            "phone_number": user.phone_number,
            "email": user.email,
            "role": user.role,
            "status": "Active" if user.status else "Non-Active",
            "created_at": user.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            "token": {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            },
            "message": "Login successful."
        }, status=200)

    except Exception as e:
        print(f"Login error: {str(e)}")
        return Response({"error": "An error occurred during login."}, status=500)












import re
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.core.mail import send_mail
from .models import CustomUser

@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password(request):
    phone_number = request.data.get('email')
    new_password = request.data.get('new_password')

    # Basic validation
    if not phone_number:
        return Response({"error": "Email is required."}, status=400)

    if not new_password:
        return Response({"error": "New password is required."}, status=400)
    
    
    print("\n Submitted data\n ")
    print("=" * 20)
    print(f" Email: {phone_number}\n Password: {new_password}\n")

    # Validate password strength
    if len(new_password) < 6:
        return Response({"error": "Password must be at least 6 characters long."}, status=400)
    if not re.search(r"[A-Z]", new_password):
        return Response({"error": "Password must contain at least one uppercase letter."}, status=400)
    if not re.search(r"[a-z]", new_password):
        return Response({"error": "Password must contain at least one lowercase letter."}, status=400)
    if not re.search(r"[0-9]", new_password):
        return Response({"error": "Password must contain at least one number."}, status=400)
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", new_password):
        return Response({"error": "Password must contain at least one special character."}, status=400)

    try:
        # Find the user
        user = CustomUser.objects.get(email=phone_number)
        
    
        # Update the user's password
        user.set_password(new_password)
        user.save()

        # Send the new password to the user's email
        send_mail(
            subject="Your New Password",
            message=f"Your password has been reset to Sunflower Production and Marketing Integration System.\n Your new password is: {new_password}",
            from_email="no-reply@format.com",
            recipient_list=[user.email],
        )
        
        print('Password Changed successfully and can now login')

        return Response({"message": "Password reset successfully. A confirmation has been sent to your email."}, status=200)

    except CustomUser.DoesNotExist:
        return Response({"error": "User with this phone number does not exist."}, status=404)






from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import CustomUser
from django.core.exceptions import ObjectDoesNotExist
from rest_framework_simplejwt.authentication import JWTAuthentication




# Delete a user by ID (admin only)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_user_by_id(request, user_id):
    
    try:
        user = CustomUser.objects.get(id=user_id)
        user.delete()
        return Response({"message": "User deleted successfully."}, status=200)
    except ObjectDoesNotExist:
        return Response({"error": "User with the given ID does not exist."}, status=404)





from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.core.exceptions import ObjectDoesNotExist
from .models import CustomUser

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.core.exceptions import ObjectDoesNotExist
from .models import CustomUser

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.core.exceptions import ObjectDoesNotExist
from .models import CustomUser  # Adjust this import as per your project structure

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_user(request, user_id):
    phone_number = request.data.get('phone_number')
    email = request.data.get('email')
    role = request.data.get('role')
    # status = request.data.get('status')

    # Validate required fields
    if not phone_number or not role:
        return Response({"message": "Phone number, email, and role are required for updating a user."}, status=400)

    try:
        user = CustomUser.objects.get(id=user_id)

        # Check if the phone number or email already exists, excluding the current user
        if CustomUser.objects.filter(phone_number=phone_number).exclude(id=user_id).exists():
            print("A user with this phone number already exists.")
            return Response({"message": "A user with this phone number already exists."}, status=400)

        if CustomUser.objects.filter(email=email).exclude(id=user_id).exists():
            print("A user with this email already exists.")
            return Response({"message": "A user with this email already exists."}, status=400)

        # Update user fields
        user.phone_number = phone_number
        user.email = email
        user.role = role
        user.status = True
        user.is_active = True
        user.save()

        return Response({"message": "User updated successfully."}, status=200)

    except ObjectDoesNotExist:
        return Response({"message": "User with the given ID does not exist."}, status=404)

    except Exception as e:
        # Catch-all for unexpected errors
        return Response({"message": f"An unexpected error occurred: {str(e)}"}, status=500)

    


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_all_users(request):
    # Retrieve all users
    users = CustomUser.objects.all().values(
        'id', 'phone_number', 'email', 'role', 'status', 'created_at',
    )

    # Convert status field to "Active" or "Non-Active"
    formatted_users = [
        {
            **user,
            "status": "Active" if user["status"] else "Non-Active"  # Convert boolean to string
        }
        for user in users
    ]

    return Response({"users": formatted_users}, status=200)




@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_by_id(request, user_id):
    try:
        user = CustomUser.objects.get(id=user_id)
        
       
        return Response({
            "id": user.id,
            "phone_number": user.phone_number,
            "email": user.email,
            "role": user.role,
            "status": "Active" if user.status else "Non-Active",
            "created_at": user.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        }, status=200)
    except ObjectDoesNotExist:
        return Response({"error": "User with the given ID does not exist."}, status=404)



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_by_email(request):
    email = request.query_params.get('email')

    if not email:
        return Response({"error": "Email is required to search for a user."}, status=400)

    try:
        user = CustomUser.objects.select_related('created_by').get(email=email)
        
        if request.user.role != 'admin' and request.user.email != email:
            return Response({"error": "You are not authorized to access this user."}, status=403)

        created_by_user = user.created_by
        return Response({
            "id": user.id,
            "phone_number": user.phone_number,
            "email": user.email,
            "role": user.role,
            "status": "Active" if user.status else "Non-Active",
            "created_at": user.created_at.strftime('%Y-%m-%d %H:%M:%S'),

        }, status=200)
    except ObjectDoesNotExist:
        return Response({"error": "User with the given email does not exist."}, status=404)



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_by_phone(request):
    phone_number = request.query_params.get('phone_number')

    if not phone_number:
        return Response({"error": "Phone number is required to search for a user."}, status=400)

    try:
        user = CustomUser.objects.select_related('created_by').get(phone_number=phone_number)
        
        if request.user.role != 'admin' and request.user.phone_number != phone_number:
            return Response({"error": "You are not authorized to access this user."}, status=403)

        created_by_user = user.created_by
        return Response({
            "id": user.id,
            "phone_number": user.phone_number,
            "email": user.email,
            "role": user.role,
            "status": "Active" if user.status else "Non-Active",
            "created_at": user.created_at.strftime('%Y-%m-%d %H:%M:%S'),

        }, status=200)
    except ObjectDoesNotExist:
        return Response({"error": "User with the given phone number does not exist."}, status=404)




@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def activate_user(request, user_id):
    try:
        # Fetch the user or return 404 if not found
        user = get_object_or_404(CustomUser, id=user_id)

        # Check if the user is already active
        if user.status:
            return Response({"message": "This user account is already activated."}, status=400)

        # Activate the user
        user.status = True
        user.save()

        return Response({"message": "User activated successfully."}, status=200)

    except Exception as e:
        return Response({"message": f"An unexpected error occurred: {str(e)}"}, status=500)




@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def deactivate_user(request, user_id):
    try:
        # Fetch the user or return 404 if not found
        user = get_object_or_404(CustomUser, id=user_id)

        # Check if the user is already deactivated
        if not user.status:
            return Response({"message": "This user account is already deactivated."}, status=400)

        # Deactivate the user
        user.status = False
        user.save()

        return Response({"message": "User deactivated successfully."}, status=200)

    except Exception as e:
        return Response({"message": f"An unexpected error occurred: {str(e)}"}, status=500)





import logging
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .serializers import ContactUsSerializer
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from rest_framework import status

# Configure logging
logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([AllowAny])
def contact_us(request):
    logger.info("Received contact request with data: %s", request.data)
    
    serializer = ContactUsSerializer(data=request.data)
    
    if serializer.is_valid():
        names = serializer.validated_data['names']
        email = serializer.validated_data['email']
        subject = serializer.validated_data['subject']
        description = serializer.validated_data['description']
        
        # Check for empty fields
        if not names.strip():
            logger.error("Name field is empty.")
            return Response({"error": "Name field cannot be empty."}, status=status.HTTP_400_BAD_REQUEST)
        if not subject.strip():
            logger.error("Subject field is empty.")
            return Response({"error": "Subject field cannot be empty."}, status=status.HTTP_400_BAD_REQUEST)
        if not description.strip():
            logger.error("Description field is empty.")
            return Response({"error": "Description field cannot be empty."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate email format
        try:
            validate_email(email)
        except ValidationError:
            logger.error("Invalid email format: %s", email)
            return Response({"error": "Invalid email format."}, status=status.HTTP_400_BAD_REQUEST)

        # Sending email
        try:
            send_mail(
                subject=f"Contact Us: {subject}",
                message=f"Name: {names}\nEmail: {email}\n\nDescription:\n{description}",
                from_email=email,
                recipient_list=['princemugabe568@gmail.com'],
                fail_silently=False,
            )
            logger.info("Email sent successfully to %s", email)
            return Response({"message": "Email sent successfully."}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception("An error occurred while sending email: %s", e)
            return Response({"error": "Failed to send email."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    logger.error("Invalid serializer data: %s", serializer.errors)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)





@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_logged_in_user(request):
    user = request.user  # Get the logged-in user

    return Response({
        "id": user.id,
        "phone_number": user.phone_number,
        "email": user.email,
        "role": user.role,
        "status": "Active" if user.status else "Non-Active",
        "created_at": user.created_at.strftime('%Y-%m-%d %H:%M:%S'),
    }, status=200)