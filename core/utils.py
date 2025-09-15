from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Gestionnaire d'exceptions personnalisé pour des réponses d'erreur cohérentes
    """
    response = exception_handler(exc, context)

    if response is not None:
        custom_response_data = {
            'error': True,
            'message': 'Une erreur est survenue',
            'details': None,
            'status_code': response.status_code
        }

        # Personnaliser les messages d'erreur selon le type
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            custom_response_data['message'] = 'Données invalides'
            custom_response_data['details'] = response.data
        elif response.status_code == status.HTTP_401_UNAUTHORIZED:
            custom_response_data['message'] = 'Authentification requise'
        elif response.status_code == status.HTTP_403_FORBIDDEN:
            custom_response_data['message'] = 'Permission refusée'
        elif response.status_code == status.HTTP_404_NOT_FOUND:
            custom_response_data['message'] = 'Ressource non trouvée'
        elif response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED:
            custom_response_data['message'] = 'Méthode non autorisée'
        elif response.status_code >= 500:
            custom_response_data['message'] = 'Erreur interne du serveur'
            # Log les erreurs serveur
            logger.error(f'Server Error: {exc}', exc_info=True)

        response.data = custom_response_data

    return response


def success_response(data=None, message="Succès", status_code=status.HTTP_200_OK):
    """
    Fonction utilitaire pour créer des réponses de succès cohérentes
    """
    response_data = {
        'success': True,
        'message': message,
        'data': data
    }
    return Response(response_data, status=status_code)


def error_response(message="Une erreur est survenue", details=None, status_code=status.HTTP_400_BAD_REQUEST):
    """
    Fonction utilitaire pour créer des réponses d'erreur cohérentes
    """
    response_data = {
        'error': True,
        'message': message,
        'details': details,
        'status_code': status_code
    }
    return Response(response_data, status=status_code)


def paginated_response(queryset, serializer_class, request, message="Données récupérées avec succès"):
    """
    Fonction utilitaire pour créer des réponses paginées cohérentes
    """
    from rest_framework.pagination import PageNumberPagination
    
    paginator = PageNumberPagination()
    page = paginator.paginate_queryset(queryset, request)
    
    if page is not None:
        serializer = serializer_class(page, many=True, context={'request': request})
        return paginator.get_paginated_response({
            'success': True,
            'message': message,
            'data': serializer.data
        })
    
    serializer = serializer_class(queryset, many=True, context={'request': request})
    return success_response(data=serializer.data, message=message)