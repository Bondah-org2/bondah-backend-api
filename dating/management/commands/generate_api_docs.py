"""
Management command to generate API documentation
"""
from django.core.management.base import BaseCommand
from django.conf import settings
import json
import os


class Command(BaseCommand):
    help = 'Generate comprehensive API documentation'

    def add_arguments(self, parser):
        parser.add_argument(
            '--format',
            type=str,
            choices=['json', 'yaml', 'html'],
            default='json',
            help='Output format for the documentation'
        )
        parser.add_argument(
            '--output',
            type=str,
            help='Output file path (default: api_schema.{format})'
        )
        parser.add_argument(
            '--serve',
            action='store_true',
            help='Start development server with documentation'
        )

    def handle(self, *args, **options):
        format_type = options['format']
        output_file = options['output']
        serve_docs = options['serve']

        if serve_docs:
            self.serve_documentation()
        else:
            self.generate_documentation(format_type, output_file)

    def generate_documentation(self, format_type, output_file):
        """Generate API documentation in specified format"""
        try:
            from drf_spectacular.generators import SchemaGenerator
            from drf_spectacular.renderers import OpenApiJsonRenderer, OpenApiYamlRenderer
            from drf_spectacular.settings import spectacular_settings
            from django.urls import get_resolver
            from django.conf import settings
            
            self.stdout.write('Generating API schema...')
            
            # Generate the schema
            generator = SchemaGenerator()
            schema = generator.get_schema()
            
            if not output_file:
                output_file = f'api_schema.{format_type}'
            
            # Render the schema
            if format_type == 'json':
                renderer = OpenApiJsonRenderer()
                content_type = 'application/json'
            elif format_type == 'yaml':
                renderer = OpenApiYamlRenderer()
                content_type = 'application/x-yaml'
            else:
                self.stdout.write(
                    self.style.ERROR(f'Unsupported format: {format_type}')
                )
                return
            
            rendered_schema = renderer.render(schema, renderer_context={})
            
            # Write to file
            with open(output_file, 'wb') as f:
                f.write(rendered_schema)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'API documentation generated successfully: {output_file}'
                )
            )
            
            # Display statistics
            self.display_statistics(schema)
            
        except ImportError as e:
            self.stdout.write(
                self.style.ERROR(f'Required package not installed: {e}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error generating documentation: {e}')
            )

    def serve_documentation(self):
        """Start development server with documentation"""
        try:
            import subprocess
            import sys
            
            self.stdout.write('Starting development server with API documentation...')
            self.stdout.write('')
            self.stdout.write('Documentation will be available at:')
            self.stdout.write('  - Swagger UI: http://localhost:8000/api/docs/')
            self.stdout.write('  - ReDoc: http://localhost:8000/api/redoc/')
            self.stdout.write('  - OpenAPI Schema: http://localhost:8000/api/schema/')
            self.stdout.write('')
            self.stdout.write('Press Ctrl+C to stop the server.')
            self.stdout.write('')
            
            # Start Django development server
            subprocess.run([sys.executable, 'manage.py', 'runserver'])
            
        except KeyboardInterrupt:
            self.stdout.write('\nServer stopped.')
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error starting server: {e}')
            )

    def display_statistics(self, schema):
        """Display API documentation statistics"""
        paths = schema.get('paths', {})
        components = schema.get('components', {})
        schemas = components.get('schemas', {})
        
        # Count endpoints by method
        method_counts = {}
        tag_counts = {}
        
        for path, methods in paths.items():
            for method, details in methods.items():
                if method.upper() in ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']:
                    method_counts[method.upper()] = method_counts.get(method.upper(), 0) + 1
                    
                    # Count by tags
                    tags = details.get('tags', ['Untagged'])
                    for tag in tags:
                        tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('API Documentation Statistics:'))
        self.stdout.write('=' * 50)
        self.stdout.write(f'Total Endpoints: {sum(method_counts.values())}')
        self.stdout.write('')
        
        self.stdout.write('Endpoints by Method:')
        for method, count in sorted(method_counts.items()):
            self.stdout.write(f'  {method}: {count}')
        
        self.stdout.write('')
        self.stdout.write('Endpoints by Category:')
        for tag, count in sorted(tag_counts.items()):
            self.stdout.write(f'  {tag}: {count}')
        
        self.stdout.write('')
        self.stdout.write(f'Total Schemas: {len(schemas)}')
        self.stdout.write('')

    def validate_schema(self, schema):
        """Validate the generated schema"""
        required_fields = ['openapi', 'info', 'paths']
        missing_fields = [field for field in required_fields if field not in schema]
        
        if missing_fields:
            self.stdout.write(
                self.style.WARNING(
                    f'Warning: Schema missing required fields: {missing_fields}'
                )
            )
            return False
        
        # Validate OpenAPI version
        openapi_version = schema.get('openapi', '')
        if not openapi_version.startswith('3.'):
            self.stdout.write(
                self.style.WARNING(
                    f'Warning: Unsupported OpenAPI version: {openapi_version}'
                )
            )
        
        return True
