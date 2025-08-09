import os
import pandas as pd
import logging
from django.conf import settings
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

# Configure logger
logger = logging.getLogger(__name__)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_datasets(request):
    """
    List all available datasets in the data directory.
    """
    try:
        # Path to data directory
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'weatherApp', 'data')
        
        # Validate data directory exists
        if not os.path.exists(data_dir):
            error_msg = f"Data directory not found: {data_dir}"
            print(f"ERROR: {error_msg}")
            logger.error(error_msg)
            return Response({'error': error_msg}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Check if directory is readable
        if not os.access(data_dir, os.R_OK):
            error_msg = f"Data directory is not readable: {data_dir}"
            print(f"ERROR: {error_msg}")
            logger.error(error_msg)
            return Response({'error': error_msg}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Get all CSV files in the data directory
        try:
            all_files = os.listdir(data_dir)
            dataset_files = [f for f in all_files if f.endswith('.csv')]
            
            # Check if any datasets were found
            if not dataset_files:
                print(f"WARNING: No CSV datasets found in {data_dir}")
                logger.warning(f"No CSV datasets found in {data_dir}")
                return Response({
                    'count': 0,
                    'datasets': [],
                    'warning': 'No datasets found'
                })
                
        except PermissionError as e:
            error_msg = f"Permission denied when accessing data directory: {data_dir}"
            print(f"ERROR: {error_msg}")
            logger.error(error_msg)
            return Response({'error': error_msg}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Get basic info about each dataset
        datasets = []
        for file_name in dataset_files:
            file_path = os.path.join(data_dir, file_name)
            
            # Validate file exists and is readable
            if not os.path.isfile(file_path):
                print(f"WARNING: {file_name} is not a valid file")
                continue
                
            if not os.access(file_path, os.R_OK):
                print(f"WARNING: {file_name} is not readable")
                continue
            
            try:
                # Get file stats
                file_stats = os.stat(file_path)
                
                # Validate file size
                if file_stats.st_size == 0:
                    print(f"WARNING: {file_name} is an empty file")
                    datasets.append({
                        'name': file_name,
                        'warning': 'Empty file',
                        'size_bytes': 0,
                        'size_human': '0 MB',
                        'last_modified': file_stats.st_mtime,
                    })
                    continue
                
                # Read the first few rows to get column info and sample data
                try:
                    df = pd.read_csv(file_path, nrows=5)
                    
                    # Validate that the file has columns
                    if len(df.columns) == 0:
                        print(f"WARNING: {file_name} has no columns")
                        datasets.append({
                            'name': file_name,
                            'warning': 'No columns detected',
                            'size_bytes': file_stats.st_size,
                            'size_human': f"{file_stats.st_size / 1024 / 1024:.2f} MB",
                            'last_modified': file_stats.st_mtime,
                        })
                        continue
                    
                    datasets.append({
                        'name': file_name,
                        'columns': list(df.columns),
                        'sample_rows': len(df),
                        'size_bytes': file_stats.st_size,
                        'size_human': f"{file_stats.st_size / 1024 / 1024:.2f} MB",
                        'last_modified': file_stats.st_mtime,
                    })
                except pd.errors.EmptyDataError:
                    print(f"WARNING: {file_name} is empty or has no data rows")
                    datasets.append({
                        'name': file_name,
                        'warning': 'Empty dataset or no data rows',
                        'size_bytes': file_stats.st_size,
                        'size_human': f"{file_stats.st_size / 1024 / 1024:.2f} MB",
                        'last_modified': file_stats.st_mtime,
                    })
                except pd.errors.ParserError as e:
                    print(f"ERROR: {file_name} has parsing issues: {str(e)}")
                    datasets.append({
                        'name': file_name,
                        'error': f'CSV parsing error: {str(e)}',
                        'size_bytes': file_stats.st_size,
                        'size_human': f"{file_stats.st_size / 1024 / 1024:.2f} MB",
                        'last_modified': file_stats.st_mtime,
                    })
            except Exception as e:
                print(f"ERROR processing {file_name}: {str(e)}")
                logger.error(f"Error processing {file_name}: {str(e)}")
                datasets.append({
                    'name': file_name,
                    'error': str(e),
                    'size_bytes': os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                    'size_human': f"{os.path.getsize(file_path) / 1024 / 1024:.2f} MB" if os.path.exists(file_path) else "0 MB",
                    'last_modified': os.path.getmtime(file_path) if os.path.exists(file_path) else None,
                })
        
        print(f"INFO: Successfully listed {len(datasets)} datasets")
        return Response({
            'count': len(datasets),
            'datasets': datasets
        })
    
    except Exception as e:
        error_msg = f"Unexpected error in list_datasets: {str(e)}"
        print(f"ERROR: {error_msg}")
        logger.error(error_msg)
        return Response({'error': error_msg}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dataset_preview(request, dataset_name):
    """
    Preview the first few rows of a specific dataset.
    """
    try:
        # Validate dataset_name parameter
        if not dataset_name:
            error_msg = "Dataset name is required"
            print(f"ERROR: {error_msg}")
            logger.error(error_msg)
            return Response({'error': error_msg}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate filename to prevent directory traversal
        if '..' in dataset_name or '/' in dataset_name or '\\' in dataset_name:
            error_msg = f"Invalid dataset name with potential directory traversal: {dataset_name}"
            print(f"ERROR: {error_msg}")
            logger.error(error_msg)
            return Response({'error': 'Invalid dataset name'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate file extension
        if not dataset_name.endswith('.csv'):
            error_msg = f"Invalid file extension. Only CSV files are supported: {dataset_name}"
            print(f"ERROR: {error_msg}")
            logger.error(error_msg)
            return Response({'error': 'Only CSV files are supported'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Path to data file
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'weatherApp', 'data')
        
        # Validate data directory exists
        if not os.path.exists(data_dir):
            error_msg = f"Data directory not found: {data_dir}"
            print(f"ERROR: {error_msg}")
            logger.error(error_msg)
            return Response({'error': error_msg}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        file_path = os.path.join(data_dir, dataset_name)
        
        # Validate file exists
        if not os.path.exists(file_path):
            error_msg = f"Dataset not found: {dataset_name}"
            print(f"ERROR: {error_msg}")
            logger.error(error_msg)
            return Response({'error': 'Dataset not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Validate file is readable
        if not os.access(file_path, os.R_OK):
            error_msg = f"Dataset is not readable: {dataset_name}"
            print(f"ERROR: {error_msg}")
            logger.error(error_msg)
            return Response({'error': 'Dataset is not readable'}, status=status.HTTP_403_FORBIDDEN)
        
        # Validate file is not empty
        if os.path.getsize(file_path) == 0:
            error_msg = f"Dataset is empty: {dataset_name}"
            print(f"ERROR: {error_msg}")
            logger.error(error_msg)
            return Response({'error': 'Dataset is empty'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate rows parameter
        try:
            rows_to_preview = int(request.GET.get('rows', 10))  # Default to 10 rows
            if rows_to_preview <= 0:
                error_msg = f"Invalid rows parameter: {rows_to_preview}. Must be greater than 0."
                print(f"ERROR: {error_msg}")
                logger.error(error_msg)
                return Response({'error': 'Rows parameter must be greater than 0'}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError:
            error_msg = f"Invalid rows parameter: {request.GET.get('rows')}. Must be an integer."
            print(f"ERROR: {error_msg}")
            logger.error(error_msg)
            return Response({'error': 'Rows parameter must be an integer'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Read the CSV file
        try:
            df = pd.read_csv(file_path, nrows=rows_to_preview)
            
            # Check if the file has any columns
            if len(df.columns) == 0:
                error_msg = f"Dataset has no columns: {dataset_name}"
                print(f"ERROR: {error_msg}")
                logger.error(error_msg)
                return Response({'error': 'Dataset has no columns'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Count total rows
            try:
                total_rows = sum(1 for _ in open(file_path)) - 1  # Subtract header row
                if total_rows < 0:
                    total_rows = 0  # Handle edge case of empty file with no header
            except Exception as e:
                print(f"WARNING: Could not count total rows in {dataset_name}: {str(e)}")
                total_rows = "Unknown"
            
            # Get column statistics
            stats = {
                'total_rows': total_rows,
                'columns': list(df.columns),
                'preview': df.head(rows_to_preview).to_dict(orient='records')
            }
            
            print(f"INFO: Successfully previewed dataset {dataset_name} ({len(df.columns)} columns, {len(df)} preview rows)")
            return Response(stats)
            
        except pd.errors.EmptyDataError:
            error_msg = f"Dataset is empty or has no data rows: {dataset_name}"
            print(f"ERROR: {error_msg}")
            logger.error(error_msg)
            return Response({'error': 'Dataset is empty or has no data rows'}, status=status.HTTP_400_BAD_REQUEST)
        
        except pd.errors.ParserError as e:
            error_msg = f"Error parsing dataset {dataset_name}: {str(e)}"
            print(f"ERROR: {error_msg}")
            logger.error(error_msg)
            return Response({'error': f'Error parsing CSV: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        error_msg = f"Unexpected error in dataset_preview for {dataset_name if 'dataset_name' in locals() else 'unknown dataset'}: {str(e)}"
        print(f"ERROR: {error_msg}")
        logger.error(error_msg)
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def update_dataset(request, dataset_name):
    """
    Update an existing dataset. Validates that the new dataset has the same columns.
    """
    temp_path = None
    backup_path = None
    
    try:
        # Validate dataset_name parameter
        if not dataset_name:
            error_msg = "Dataset name is required"
            print(f"ERROR: {error_msg}")
            logger.error(error_msg)
            return Response({'error': error_msg}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate filename to prevent directory traversal
        if '..' in dataset_name or '/' in dataset_name or '\\' in dataset_name :
            error_msg = f"Invalid dataset name with potential directory traversal: {dataset_name}"
            print(f"ERROR: {error_msg}")
            logger.error(error_msg)
            return Response({'error': 'Invalid dataset name'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate file extension
        if not dataset_name.endswith('.csv'):
            error_msg = f"Invalid file extension. Only CSV files are supported: {dataset_name}"
            print(f"ERROR: {error_msg}")
            logger.error(error_msg)
            return Response({'error': 'Only CSV files are supported'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if file was uploaded
        if 'file' not in request.FILES:
            error_msg = "No file uploaded"
            print(f"ERROR: {error_msg}")
            logger.error(error_msg)
            return Response({'error': error_msg}, status=status.HTTP_400_BAD_REQUEST)
        
        uploaded_file = request.FILES['file']
        
        # Validate uploaded file
        if not uploaded_file:
            error_msg = "Uploaded file is invalid"
            print(f"ERROR: {error_msg}")
            logger.error(error_msg)
            return Response({'error': error_msg}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate file type
        if not uploaded_file.name.endswith('.csv'):
            error_msg = f"Invalid uploaded file extension for {uploaded_file.name}. Only CSV files are supported."
            print(f"ERROR: {error_msg}")
            logger.error(error_msg)
            return Response({'error': 'Only CSV files are supported'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate file size
        if uploaded_file.size == 0:
            error_msg = "Uploaded file is empty"
            print(f"ERROR: {error_msg}")
            logger.error(error_msg)
            return Response({'error': error_msg}, status=status.HTTP_400_BAD_REQUEST)
        
        # Define maximum file size (e.g., 100MB)
        max_size = 100 * 1024 * 1024  # 100MB in bytes
        if uploaded_file.size > max_size:
            error_msg = f"Uploaded file is too large ({uploaded_file.size} bytes). Maximum size is {max_size} bytes."
            print(f"ERROR: {error_msg}")
            logger.error(error_msg)
            return Response({'error': 'Uploaded file is too large'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Path to the existing data file
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'weatherApp', 'data')
        
        # Validate data directory exists and is writable
        if not os.path.exists(data_dir):
            error_msg = f"Data directory not found: {data_dir}"
            print(f"ERROR: {error_msg}")
            logger.error(error_msg)
            return Response({'error': error_msg}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        if not os.access(data_dir, os.W_OK):
            error_msg = f"Data directory is not writable: {data_dir}"
            print(f"ERROR: {error_msg}")
            logger.error(error_msg)
            return Response({'error': 'Data directory is not writable'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        existing_file_path = os.path.join(data_dir, dataset_name)
        
        # Validate existing file
        if not os.path.exists(existing_file_path):
            error_msg = f"Dataset not found: {dataset_name}"
            print(f"ERROR: {error_msg}")
            logger.error(error_msg)
            return Response({'error': 'Dataset not found'}, status=status.HTTP_404_NOT_FOUND)
        
        if not os.access(existing_file_path, os.R_OK):
            error_msg = f"Existing dataset is not readable: {dataset_name}"
            print(f"ERROR: {error_msg}")
            logger.error(error_msg)
            return Response({'error': 'Existing dataset is not readable'}, status=status.HTTP_403_FORBIDDEN)
        
        if not os.access(existing_file_path, os.W_OK):
            error_msg = f"Existing dataset is not writable: {dataset_name}"
            print(f"ERROR: {error_msg}")
            logger.error(error_msg)
            return Response({'error': 'Existing dataset is not writable'}, status=status.HTTP_403_FORBIDDEN)
        
        # Save the uploaded file temporarily
        temp_path = os.path.join(data_dir, f"temp_{uploaded_file.name}")
        
        try:
            with open(temp_path, 'wb') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)
        except Exception as e:
            error_msg = f"Error saving uploaded file: {str(e)}"
            print(f"ERROR: {error_msg}")
            logger.error(error_msg)
            return Response({'error': error_msg}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        try:
            # Load both datasets to compare columns
            try:
                existing_df = pd.read_csv(existing_file_path, nrows=0)  # Just get headers
            except pd.errors.EmptyDataError:
                error_msg = f"Existing dataset is empty: {dataset_name}"
                print(f"ERROR: {error_msg}")
                logger.error(error_msg)
                return Response({'error': error_msg}, status=status.HTTP_400_BAD_REQUEST)
            except pd.errors.ParserError as e:
                error_msg = f"Error parsing existing dataset {dataset_name}: {str(e)}"
                print(f"ERROR: {error_msg}")
                logger.error(error_msg)
                return Response({'error': f'Error parsing existing CSV: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                new_df = pd.read_csv(temp_path, nrows=0)  # Just get headers
            except pd.errors.EmptyDataError:
                error_msg = f"Uploaded dataset is empty"
                print(f"ERROR: {error_msg}")
                logger.error(error_msg)
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return Response({'error': error_msg}, status=status.HTTP_400_BAD_REQUEST)
            except pd.errors.ParserError as e:
                error_msg = f"Error parsing uploaded dataset: {str(e)}"
                print(f"ERROR: {error_msg}")
                logger.error(error_msg)
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return Response({'error': f'Error parsing uploaded CSV: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if columns are empty
            if len(existing_df.columns) == 0:
                error_msg = f"Existing dataset has no columns: {dataset_name}"
                print(f"ERROR: {error_msg}")
                logger.error(error_msg)
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return Response({'error': error_msg}, status=status.HTTP_400_BAD_REQUEST)
            
            if len(new_df.columns) == 0:
                error_msg = "Uploaded dataset has no columns"
                print(f"ERROR: {error_msg}")
                logger.error(error_msg)
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return Response({'error': error_msg}, status=status.HTTP_400_BAD_REQUEST)
            
            existing_columns = set(existing_df.columns)
            new_columns = set(new_df.columns)
            
            # Check if columns match
            if existing_columns != new_columns:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                
                # Return error with details
                missing_columns = existing_columns - new_columns
                extra_columns = new_columns - existing_columns
                
                error_details = {
                    'error': 'Column mismatch between datasets',
                    'existing_columns': list(existing_columns),
                    'new_columns': list(new_columns)
                }
                
                if missing_columns:
                    error_details['missing_columns'] = list(missing_columns)
                    print(f"ERROR: Missing columns in uploaded dataset: {missing_columns}")
                
                if extra_columns:
                    error_details['extra_columns'] = list(extra_columns)
                    print(f"ERROR: Extra columns in uploaded dataset: {extra_columns}")
                
                logger.error(f"Column mismatch for dataset {dataset_name}")
                return Response(error_details, status=status.HTTP_400_BAD_REQUEST)
            
            # Columns match, proceed with replacement
            # Create backup of the existing file
            backup_path = os.path.join(data_dir, f"{dataset_name}.bak")
            
            # Check if backup file already exists and remove it if it does
            if os.path.exists(backup_path):
                try:
                    os.remove(backup_path)
                except Exception as e:
                    error_msg = f"Error removing existing backup file: {str(e)}"
                    print(f"ERROR: {error_msg}")
                    logger.error(error_msg)
                    # Clean up temporary file
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    return Response({'error': error_msg}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            try:
                os.rename(existing_file_path, backup_path)
            except Exception as e:
                error_msg = f"Error creating backup file: {str(e)}"
                print(f"ERROR: {error_msg}")
                logger.error(error_msg)
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return Response({'error': error_msg}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Move the new file into place
            try:
                os.rename(temp_path, existing_file_path)
            except Exception as e:
                # Restore backup if rename fails
                error_msg = f"Error moving new file into place: {str(e)}"
                print(f"ERROR: {error_msg}")
                logger.error(error_msg)
                
                # Restore backup
                try:
                    if os.path.exists(backup_path):
                        os.rename(backup_path, existing_file_path)
                except Exception as restore_error:
                    print(f"CRITICAL ERROR: Failed to restore backup after failed update: {str(restore_error)}")
                    logger.critical(f"Failed to restore backup after failed update: {str(restore_error)}")
                
                # Clean up temporary file if it still exists
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    
                return Response({'error': error_msg}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Load basic info about the new dataset
            try:
                new_df = pd.read_csv(existing_file_path, nrows=5)
                total_rows = sum(1 for _ in open(existing_file_path)) - 1  # Subtract header row
                file_stats = os.stat(existing_file_path)
                
                print(f"INFO: Successfully updated dataset {dataset_name}")
                logger.info(f"Successfully updated dataset {dataset_name}")
                
                # Remove backup if everything is successful
                try:
                    if os.path.exists(backup_path):
                        os.remove(backup_path)
                        backup_path = None
                except Exception as e:
                    print(f"WARNING: Failed to remove backup file: {str(e)}")
                    logger.warning(f"Failed to remove backup file: {str(e)}")
                
                return Response({
                    'success': True,
                    'message': f'Dataset {dataset_name} successfully updated',
                    'rows': total_rows,
                    'columns': list(new_df.columns),
                    'size_bytes': file_stats.st_size,
                    'size_human': f"{file_stats.st_size / 1024 / 1024:.2f} MB",
                })
                
            except Exception as e:
                error_msg = f"Error reading updated dataset: {str(e)}"
                print(f"ERROR: {error_msg}")
                logger.error(error_msg)
                
                # Try to restore from backup if reading fails
                try:
                    if os.path.exists(backup_path):
                        if os.path.exists(existing_file_path):
                            os.remove(existing_file_path)
                        os.rename(backup_path, existing_file_path)
                        backup_path = None
                        print(f"INFO: Restored backup after error reading updated dataset")
                except Exception as restore_error:
                    print(f"CRITICAL ERROR: Failed to restore backup after failed update: {str(restore_error)}")
                    logger.critical(f"Failed to restore backup after failed update: {str(restore_error)}")
                
                return Response({'error': error_msg}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        except Exception as e:
            error_msg = f"Unexpected error updating dataset: {str(e)}"
            print(f"ERROR: {error_msg}")
            logger.error(error_msg)
            
            # Clean up temporary files
            if os.path.exists(temp_path):
                os.remove(temp_path)
                temp_path = None
            
            # If backup exists, restore it
            try:
                if os.path.exists(backup_path) and not os.path.exists(existing_file_path):
                    os.rename(backup_path, existing_file_path)
                    backup_path = None
                    print(f"INFO: Restored backup after exception")
            except Exception as restore_error:
                print(f"CRITICAL ERROR: Failed to restore backup after exception: {str(restore_error)}")
                logger.critical(f"Failed to restore backup after exception: {str(restore_error)}")
                
            return Response({'error': error_msg}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Exception as e:
        error_msg = f"Unexpected error in update_dataset for {dataset_name if 'dataset_name' in locals() else 'unknown dataset'}: {str(e)}"
        print(f"ERROR: {error_msg}")
        logger.error(error_msg)
        
        # Clean up resources
        try:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
                
            if backup_path and os.path.exists(backup_path) and not os.path.exists(existing_file_path):
                os.rename(backup_path, existing_file_path)
                print(f"INFO: Restored backup after critical error")
        except Exception as cleanup_error:
            print(f"CRITICAL ERROR: Failed in cleanup after critical error: {str(cleanup_error)}")
            logger.critical(f"Failed in cleanup after critical error: {str(cleanup_error)}")
            
        return Response({'error': error_msg}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    finally:
        # Final cleanup
        try:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
                print(f"INFO: Cleaned up temporary file")
        except Exception as e:
            print(f"WARNING: Failed to clean up temporary file: {str(e)}")
            logger.warning(f"Failed to clean up temporary file: {str(e)}")