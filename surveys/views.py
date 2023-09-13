from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework.decorators import api_view,action
from .models import Candidate,Survey,Question,Response
from .serializers import CandidateSerializer,SurveySerializer, QuestionSerializer, ResponseSerializer
from django.db.models import Count, Case, When, F, Value, IntegerField

def calculate_similarity(candidate1, candidate2):
    # Retrieve responses for both candidates
    responses_candidate1 = Response.objects.filter(candidate=candidate1).exclude(selected_option__isnull=True)
    responses_candidate2 = Response.objects.filter(candidate=candidate2).exclude(selected_option__isnull=True)

    # Calculate the number of matching responses
    matching_responses = 0
    total_responses = max(len(responses_candidate1), len(responses_candidate2))

    for response1 in responses_candidate1:
        for response2 in responses_candidate2:
            if response1.question == response2.question and response1.selected_option == response2.selected_option:
                matching_responses += 1

    # Calculate similarity percentage
    similarity_percentage = (matching_responses / total_responses) * 100

    return similarity_percentage

@api_view(['GET'])
def candidate_similarity(request, candidate_id):
    candidate = get_object_or_404(Candidate, id=candidate_id)
    candidates = Candidate.objects.exclude(id=candidate_id)

    similarity_scores = {}

    for other_candidate in candidates:
        similarity = calculate_similarity(candidate, other_candidate)
        similarity_scores[other_candidate.name] = similarity

    sorted_similarity_scores = dict(sorted(similarity_scores.items(), key=lambda item: item[1], reverse=True))

    return Response(sorted_similarity_scores)

class SurveyViewSet(viewsets.ModelViewSet):
    queryset = Survey.objects.all()
    serializer_class = SurveySerializer

    @action(detail=True, methods=['post'])
    def create_survey_with_questions(self, request, pk=None):
        survey = self.get_object()
        for i in range(20):
            Question.objects.create(survey=survey, text=f"Question {i+1}")
        return Response({'message': 'Survey created with 20 questions.'})

class ResponseViewSet(viewsets.ModelViewSet):
    queryset = Response.objects.all()
    serializer_class = ResponseSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'message': 'Response submitted successfully.'})

class CandidateViewSet(viewsets.ModelViewSet):
    queryset = Candidate.objects.all()
    serializer_class = CandidateSerializer

    @action(detail=True, methods=['get'])
    def similarity(self, request, pk=None):
        candidate = self.get_object()
        responses_candidate = Response.objects.filter(candidate=candidate)

        # Create a subquery to count matching responses for each candidate
        subquery = Response.objects.exclude(candidate=candidate).annotate(
            matching_responses=Count(
                Case(
                    When(
                        candidate=candidate,
                        selected_option=F('selected_option'),
                        then=Value(1)
                    ),
                    default=Value(0),
                    output_field=IntegerField()
                )
            )
        )

        # Calculate similarity and create a list of similar candidates
        similarity_scores = []
        for other_candidate in Candidate.objects.exclude(id=candidate.id):
            matching_responses = subquery.filter(candidate=other_candidate)
            total_responses = max(len(responses_candidate), len(matching_responses))
            similarity_percentage = (matching_responses[0].matching_responses / total_responses) * 100
            similarity_scores.append({
                'candidate_id': other_candidate.id,
                'candidate_name': other_candidate.name,
                'similarity_percentage': similarity_percentage
            })

        # Sort similarity scores in descending order
        similarity_scores = sorted(similarity_scores, key=lambda x: x['similarity_percentage'], reverse=True)

        # Pagination logic
        page = self.paginate_queryset(similarity_scores)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        return Response(similarity_scores)