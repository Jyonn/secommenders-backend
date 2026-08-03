from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase
from django.urls import reverse

from evaluation.views import parse_evaluation_filters


class EvaluationFilterTests(SimpleTestCase):
    @patch('evaluation.views.get_leaderboard', return_value=[])
    def test_parser_supports_repeated_and_comma_separated_values(self, _get_leaderboard):
        response = self.client.get(
            reverse('evaluation-leaderboard'),
            {
                'plan_name': ['Grid_A,grid_b', 'grid_c'],
                'data_name': 'RAF',
                'run_id': 'Run_A',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()['applied_filters'],
            {
                'plan_name': ['grid_a', 'grid_b', 'grid_c'],
                'data_name': ['raf'],
                'run_id': ['Run_A'],
            },
        )

    @patch('evaluation.views.get_leaderboard', return_value=[])
    def test_leaderboard_passes_plan_and_data_filters(self, get_leaderboard):
        response = self.client.get(
            reverse('evaluation-leaderboard'),
            {
                'metric': 'ndcg@10',
                'plan_name': 'qwen08b_grid1_ebs64',
                'data_name': 'raf',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['api_version'], 'leaderboard.filters.v2')
        get_leaderboard.assert_called_once()
        kwargs = get_leaderboard.call_args.kwargs
        self.assertEqual(kwargs['plan_name'], ['qwen08b_grid1_ebs64'])
        self.assertEqual(kwargs['data_name'], ['raf'])

    def test_empty_filters_are_omitted(self):
        request = RequestFactory().get(reverse('evaluation-leaderboard'))

        self.assertEqual(parse_evaluation_filters(request.GET), {})
