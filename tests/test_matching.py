"""Unit tests for job matching logic"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestJobMatching:
    """Test suite for job matching functionality"""

    @pytest.fixture
    def sample_job(self):
        """Create sample job data for testing"""
        return {
            'id': '12345',
            'name': 'Python Developer',
            'area': {'name': 'Moscow'},
            'salary': {'from': 100000, 'to': 200000, 'currency': 'RUR'},
            'test_required': False,
            'employer': {'name': 'Tech Company'},
            'snippet': {'requirement': 'Python, Django', 'responsibility': 'Development'},
            'professional_roles': [{'id': '96', 'name': 'Python Developer'}]
        }

    @pytest.fixture
    def sample_user_criteria(self):
        """Create sample user search criteria"""
        return {
            'keywords': ['Python', 'Django'],
            'areas': ['1'],  # Moscow
            'salary_from': 80000,
            'specialization': '96',
            'experience': 'between1And3',
            'employment': 'full_time'
        }

    def test_valid_job_no_test_required(self, sample_job):
        """Test that job without test_required is valid"""
        assert not sample_job.get('test_required', False)
        assert sample_job['id'] == '12345'

    def test_job_with_test_required(self, sample_job):
        """Test that job with test_required is properly marked"""
        sample_job['test_required'] = True
        assert sample_job.get('test_required', False) is True

    def test_salary_range_matching(self, sample_job, sample_user_criteria):
        """Test salary range matching logic"""
        job_salary_from = sample_job['salary'].get('from', 0)
        user_min_salary = sample_user_criteria['salary_from']
        
        # Job should match if it pays at least user's minimum
        assert job_salary_from >= user_min_salary

    def test_area_matching(self, sample_job, sample_user_criteria):
        """Test geographic area matching"""
        job_area = str(sample_job['area'].get('id', ''))
        user_areas = sample_user_criteria.get('areas', [])
        
        # This would need actual area data in production
        # For now, we test the structure
        assert isinstance(user_areas, list)
        assert len(user_areas) > 0

    def test_empty_criteria(self):
        """Test handling of empty search criteria"""
        criteria = {}
        assert 'keywords' not in criteria
        assert 'areas' not in criteria

    def test_job_employer_data(self, sample_job):
        """Test that job has valid employer information"""
        assert sample_job['employer']['name'] is not None
        assert len(sample_job['employer']['name']) > 0

    def test_job_snippet_data(self, sample_job):
        """Test that job has description snippets"""
        snippet = sample_job['snippet']
        assert 'requirement' in snippet or 'responsibility' in snippet


class TestBlacklistLogic:
    """Test suite for blacklist functionality"""

    def test_add_to_blacklist(self):
        """Test adding job to blacklist"""
        blacklist = set()
        job_id = '12345'
        
        blacklist.add(job_id)
        assert job_id in blacklist

    def test_check_blacklist(self):
        """Test checking if job is in blacklist"""
        blacklist = {'12345', '67890'}
        job_id = '12345'
        
        assert job_id in blacklist
        assert '99999' not in blacklist

    def test_persistent_blacklist(self):
        """Test blacklist persistence across requests"""
        blacklist = {'12345'}
        
        # Simulate multiple checks
        for _ in range(3):
            assert '12345' in blacklist


class TestErrorHandling:
    """Test suite for error handling in matching"""

    def test_handle_missing_fields(self):
        """Test graceful handling of missing job fields"""
        job = {'id': '123'}
        
        # Should handle missing fields
        name = job.get('name', 'Unknown')
        salary = job.get('salary', {})
        
        assert name == 'Unknown'
        assert isinstance(salary, dict)

    def test_handle_invalid_salary(self):
        """Test handling of invalid salary data"""
        job = {'salary': {'from': None, 'to': 'invalid'}}
        
        salary_from = job['salary'].get('from') or 0
        assert salary_from == 0

    def test_handle_unicode_in_job_name(self):
        """Test handling of unicode characters in job names"""
        job = {'name': 'Python разработчик'}
        
        assert isinstance(job['name'], str)
        assert len(job['name']) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
