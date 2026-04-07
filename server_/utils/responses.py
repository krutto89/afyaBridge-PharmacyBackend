from rest_framework.response import Response
from rest_framework import status
 
def success(data=None, message='Success', status_code=status.HTTP_200_OK):
    return Response({'success': True, 'message': message, 'data': data}, status=status_code)
 
def created(data=None, message='Created'):
    return Response({'success': True, 'message': message, 'data': data}, status=status.HTTP_201_CREATED)
 
def error(message='An error occurred', errors=None, status_code=status.HTTP_400_BAD_REQUEST):
    return Response({'success': False, 'message': message, 'errors': errors}, status=status_code)
 
def not_found(message='Not found'):
    return Response({'success': False, 'message': message}, status=status.HTTP_404_NOT_FOUND)

def forbidden(message='Permission denied'):
    return Response({'success': False, 'message': message}, status=status.HTTP_403_FORBIDDEN)
