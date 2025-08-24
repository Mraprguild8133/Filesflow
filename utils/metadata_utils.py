"""
Advanced metadata extraction and manipulation utilities
Supports video, audio, image, and document metadata
"""

import logging
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

# Try to import optional metadata libraries
try:
    from mutagen import File as MutagenFile
    from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, APIC
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False
    logger.warning("Mutagen not available - audio metadata features limited")

try:
    from PIL import Image
    from PIL.ExifTags import TAGS
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("PIL not available - image metadata features limited")

try:
    import ffmpeg
    FFMPEG_AVAILABLE = True
except ImportError:
    FFMPEG_AVAILABLE = False
    logger.warning("ffmpeg-python not available - video metadata features limited")

logger = logging.getLogger(__name__)

class MetadataUtils:
    """Advanced metadata extraction and manipulation"""
    
    def __init__(self):
        self.supported_formats = {
            'audio': ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.wma', '.opus'],
            'video': ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.3gp'],
            'image': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff'],
            'document': ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']
        }
    
    async def extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract comprehensive metadata from file"""
        try:
            if not os.path.exists(file_path):
                return {'error': 'File not found'}
            
            metadata = {
                'file_info': self._get_basic_file_info(file_path),
                'format_specific': {},
                'extracted_at': datetime.now().isoformat()
            }
            
            # Determine file type and extract appropriate metadata
            file_ext = os.path.splitext(file_path)[1].lower()
            
            if file_ext in self.supported_formats['audio']:
                metadata['format_specific'] = await self._extract_audio_metadata(file_path)
            elif file_ext in self.supported_formats['video']:
                metadata['format_specific'] = await self._extract_video_metadata(file_path)
            elif file_ext in self.supported_formats['image']:
                metadata['format_specific'] = await self._extract_image_metadata(file_path)
            elif file_ext in self.supported_formats['document']:
                metadata['format_specific'] = await self._extract_document_metadata(file_path)
            else:
                metadata['format_specific'] = {'unsupported_format': True}
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error extracting metadata from {file_path}: {e}")
            return {'error': str(e)}
    
    def _get_basic_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get basic file information"""
        try:
            stat_info = os.stat(file_path)
            
            return {
                'filename': os.path.basename(file_path),
                'size': stat_info.st_size,
                'size_formatted': self._format_size(stat_info.st_size),
                'created': datetime.fromtimestamp(stat_info.st_ctime).isoformat(),
                'modified': datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                'extension': os.path.splitext(file_path)[1].lower(),
                'absolute_path': os.path.abspath(file_path)
            }
            
        except Exception as e:
            logger.error(f"Error getting basic file info: {e}")
            return {'error': str(e)}
    
    async def _extract_audio_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract audio metadata using Mutagen"""
        try:
            metadata = {
                'type': 'audio',
                'available_extractors': []
            }
            
            if MUTAGEN_AVAILABLE:
                metadata['available_extractors'].append('mutagen')
                
                try:
                    audio_file = MutagenFile(file_path)
                    
                    if audio_file is not None:
                        # Basic audio properties
                        if hasattr(audio_file, 'info'):
                            info = audio_file.info
                            metadata.update({
                                'duration': getattr(info, 'length', 0),
                                'duration_formatted': self._format_duration(getattr(info, 'length', 0)),
                                'bitrate': getattr(info, 'bitrate', 0),
                                'sample_rate': getattr(info, 'sample_rate', 0),
                                'channels': getattr(info, 'channels', 0),
                                'format': getattr(info, 'mime', [''])[0] if hasattr(info, 'mime') else ''
                            })
                        
                        # Tags/metadata
                        if audio_file.tags:
                            tags = {}
                            
                            # Common tag mappings
                            tag_mappings = {
                                'TIT2': 'title',      # ID3v2
                                'TPE1': 'artist',     # ID3v2
                                'TALB': 'album',      # ID3v2
                                'TDRC': 'date',       # ID3v2
                                'TCON': 'genre',      # ID3v2
                                'TPE2': 'albumartist', # ID3v2
                                'TRCK': 'track',      # ID3v2
                                'TITLE': 'title',    # Vorbis comment
                                'ARTIST': 'artist',  # Vorbis comment
                                'ALBUM': 'album',    # Vorbis comment
                                'DATE': 'date',      # Vorbis comment
                                'GENRE': 'genre',    # Vorbis comment
                                '\xa9nam': 'title',  # MP4
                                '\xa9ART': 'artist', # MP4
                                '\xa9alb': 'album',  # MP4
                                '\xa9day': 'date',   # MP4
                                '\xa9gen': 'genre'   # MP4
                            }
                            
                            for key, value in audio_file.tags.items():
                                clean_key = tag_mappings.get(key, key)
                                
                                if isinstance(value, list) and len(value) > 0:
                                    tags[clean_key] = str(value[0])
                                else:
                                    tags[clean_key] = str(value)
                            
                            metadata['tags'] = tags
                        
                        # Album art detection
                        if hasattr(audio_file, 'tags') and audio_file.tags:
                            has_artwork = False
                            
                            # Check for ID3 artwork (APIC)
                            for key in audio_file.tags.keys():
                                if key.startswith('APIC'):
                                    has_artwork = True
                                    break
                            
                            # Check for MP4 artwork (covr)
                            if 'covr' in audio_file.tags:
                                has_artwork = True
                            
                            metadata['has_artwork'] = has_artwork
                
                except Exception as e:
                    logger.warning(f"Mutagen extraction failed: {e}")
                    metadata['mutagen_error'] = str(e)
            
            # Fallback to ffmpeg if available
            if FFMPEG_AVAILABLE:
                metadata['available_extractors'].append('ffmpeg')
                try:
                    ffmpeg_metadata = await self._extract_ffmpeg_metadata(file_path)
                    if ffmpeg_metadata:
                        metadata['ffmpeg_data'] = ffmpeg_metadata
                except Exception as e:
                    logger.warning(f"FFmpeg extraction failed: {e}")
                    metadata['ffmpeg_error'] = str(e)
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error extracting audio metadata: {e}")
            return {'error': str(e), 'type': 'audio'}
    
    async def _extract_video_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract video metadata using FFmpeg"""
        try:
            metadata = {
                'type': 'video',
                'available_extractors': []
            }
            
            if FFMPEG_AVAILABLE:
                metadata['available_extractors'].append('ffmpeg')
                
                try:
                    # Get video info
                    probe = ffmpeg.probe(file_path)
                    
                    # General format info
                    format_info = probe.get('format', {})
                    metadata.update({
                        'duration': float(format_info.get('duration', 0)),
                        'duration_formatted': self._format_duration(float(format_info.get('duration', 0))),
                        'size': int(format_info.get('size', 0)),
                        'bitrate': int(format_info.get('bit_rate', 0)),
                        'format_name': format_info.get('format_name', ''),
                        'format_long_name': format_info.get('format_long_name', '')
                    })
                    
                    # Stream information
                    streams = probe.get('streams', [])
                    video_streams = []
                    audio_streams = []
                    subtitle_streams = []
                    
                    for stream in streams:
                        if stream['codec_type'] == 'video':
                            video_streams.append({
                                'codec': stream.get('codec_name', ''),
                                'codec_long_name': stream.get('codec_long_name', ''),
                                'width': stream.get('width', 0),
                                'height': stream.get('height', 0),
                                'aspect_ratio': stream.get('display_aspect_ratio', ''),
                                'frame_rate': stream.get('r_frame_rate', ''),
                                'pixel_format': stream.get('pix_fmt', ''),
                                'bitrate': int(stream.get('bit_rate', 0)) if stream.get('bit_rate') else 0
                            })
                        elif stream['codec_type'] == 'audio':
                            audio_streams.append({
                                'codec': stream.get('codec_name', ''),
                                'codec_long_name': stream.get('codec_long_name', ''),
                                'sample_rate': int(stream.get('sample_rate', 0)) if stream.get('sample_rate') else 0,
                                'channels': stream.get('channels', 0),
                                'channel_layout': stream.get('channel_layout', ''),
                                'bitrate': int(stream.get('bit_rate', 0)) if stream.get('bit_rate') else 0
                            })
                        elif stream['codec_type'] == 'subtitle':
                            subtitle_streams.append({
                                'codec': stream.get('codec_name', ''),
                                'language': stream.get('tags', {}).get('language', 'unknown')
                            })
                    
                    metadata.update({
                        'video_streams': video_streams,
                        'audio_streams': audio_streams,
                        'subtitle_streams': subtitle_streams,
                        'stream_count': len(streams)
                    })
                    
                    # Extract tags/metadata
                    tags = format_info.get('tags', {})
                    if tags:
                        cleaned_tags = {}
                        for key, value in tags.items():
                            # Clean up tag names
                            clean_key = key.lower().replace('-', '_')
                            cleaned_tags[clean_key] = value
                        metadata['tags'] = cleaned_tags
                
                except Exception as e:
                    logger.warning(f"FFmpeg video extraction failed: {e}")
                    metadata['ffmpeg_error'] = str(e)
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error extracting video metadata: {e}")
            return {'error': str(e), 'type': 'video'}
    
    async def _extract_image_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract image metadata using PIL"""
        try:
            metadata = {
                'type': 'image',
                'available_extractors': []
            }
            
            if PIL_AVAILABLE:
                metadata['available_extractors'].append('pil')
                
                try:
                    with Image.open(file_path) as img:
                        # Basic image info
                        metadata.update({
                            'width': img.width,
                            'height': img.height,
                            'format': img.format,
                            'mode': img.mode,
                            'size_formatted': f"{img.width}x{img.height}",
                            'has_transparency': img.mode in ('RGBA', 'LA') or 'transparency' in img.info
                        })
                        
                        # Color palette info
                        if hasattr(img, 'palette') and img.palette:
                            metadata['has_palette'] = True
                            metadata['palette_size'] = len(img.palette.getdata()[1])
                        else:
                            metadata['has_palette'] = False
                        
                        # EXIF data
                        if hasattr(img, '_getexif') and img._getexif():
                            exif_data = {}
                            exif = img._getexif()
                            
                            for tag_id, value in exif.items():
                                tag = TAGS.get(tag_id, tag_id)
                                
                                # Convert value to string if it's not serializable
                                if isinstance(value, (str, int, float)):
                                    exif_data[tag] = value
                                elif isinstance(value, bytes):
                                    exif_data[tag] = f"<binary data: {len(value)} bytes>"
                                else:
                                    exif_data[tag] = str(value)
                            
                            metadata['exif'] = exif_data
                        
                        # Image info from file
                        if img.info:
                            file_info = {}
                            for key, value in img.info.items():
                                if isinstance(value, (str, int, float)):
                                    file_info[key] = value
                                else:
                                    file_info[key] = str(value)
                            metadata['file_info'] = file_info
                
                except Exception as e:
                    logger.warning(f"PIL image extraction failed: {e}")
                    metadata['pil_error'] = str(e)
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error extracting image metadata: {e}")
            return {'error': str(e), 'type': 'image'}
    
    async def _extract_document_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract document metadata (basic implementation)"""
        try:
            metadata = {
                'type': 'document',
                'available_extractors': ['basic']
            }
            
            # Basic document info (could be extended with libraries like PyPDF2, python-docx, etc.)
            file_ext = os.path.splitext(file_path)[1].lower()
            
            metadata.update({
                'document_type': file_ext[1:] if file_ext else 'unknown',
                'extractable': file_ext in ['.txt', '.json', '.xml', '.csv']
            })
            
            # For text files, get basic stats
            if file_ext == '.txt':
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        metadata.update({
                            'character_count': len(content),
                            'line_count': content.count('\n') + 1,
                            'word_count': len(content.split()),
                            'encoding': 'utf-8'
                        })
                except Exception as e:
                    logger.warning(f"Text file analysis failed: {e}")
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error extracting document metadata: {e}")
            return {'error': str(e), 'type': 'document'}
    
    async def _extract_ffmpeg_metadata(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Extract metadata using FFmpeg probe"""
        try:
            if not FFMPEG_AVAILABLE:
                return None
            
            probe = ffmpeg.probe(file_path)
            return {
                'format': probe.get('format', {}),
                'streams': probe.get('streams', [])
            }
            
        except Exception as e:
            logger.warning(f"FFmpeg probe failed: {e}")
            return None
    
    async def edit_audio_metadata(self, file_path: str, metadata_updates: Dict[str, Any]) -> bool:
        """Edit audio file metadata"""
        try:
            if not MUTAGEN_AVAILABLE:
                logger.error("Mutagen not available for metadata editing")
                return False
            
            audio_file = MutagenFile(file_path)
            if audio_file is None:
                logger.error("Could not open audio file for editing")
                return False
            
            # Ensure tags exist
            if audio_file.tags is None:
                audio_file.add_tags()
            
            # Update tags based on file format
            if file_path.lower().endswith('.mp3'):
                # ID3 tags for MP3
                tag_map = {
                    'title': 'TIT2',
                    'artist': 'TPE1',
                    'album': 'TALB',
                    'date': 'TDRC',
                    'genre': 'TCON'
                }
                
                for key, value in metadata_updates.items():
                    if key in tag_map:
                        audio_file.tags[tag_map[key]] = str(value)
            
            else:
                # Generic tags for other formats
                for key, value in metadata_updates.items():
                    if key in ['title', 'artist', 'album', 'date', 'genre']:
                        audio_file.tags[key.upper()] = str(value)
            
            audio_file.save()
            logger.info(f"Successfully updated metadata for {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error editing audio metadata: {e}")
            return False
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0 B"
        
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        
        return f"{size_bytes:.1f} PB"
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in human readable format"""
        if seconds == 0:
            return "0:00"
        
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes}:{secs:02d}"
    
    def get_metadata_summary(self, metadata: Dict[str, Any]) -> str:
        """Generate human-readable metadata summary"""
        try:
            if 'error' in metadata:
                return f"❌ Error: {metadata['error']}"
            
            summary = "📊 **Metadata Summary**\n\n"
            
            # Basic file info
            file_info = metadata.get('file_info', {})
            summary += f"📁 **File:** {file_info.get('filename', 'Unknown')}\n"
            summary += f"📏 **Size:** {file_info.get('size_formatted', 'Unknown')}\n"
            
            # Format-specific info
            format_data = metadata.get('format_specific', {})
            file_type = format_data.get('type', 'unknown')
            
            if file_type == 'audio':
                if 'duration_formatted' in format_data:
                    summary += f"⏱️ **Duration:** {format_data['duration_formatted']}\n"
                if 'bitrate' in format_data and format_data['bitrate']:
                    summary += f"🎵 **Bitrate:** {format_data['bitrate']} kbps\n"
                
                # Tags
                tags = format_data.get('tags', {})
                if 'title' in tags:
                    summary += f"🎵 **Title:** {tags['title']}\n"
                if 'artist' in tags:
                    summary += f"👤 **Artist:** {tags['artist']}\n"
                if 'album' in tags:
                    summary += f"💿 **Album:** {tags['album']}\n"
            
            elif file_type == 'video':
                if 'duration_formatted' in format_data:
                    summary += f"⏱️ **Duration:** {format_data['duration_formatted']}\n"
                
                video_streams = format_data.get('video_streams', [])
                if video_streams:
                    v_stream = video_streams[0]
                    if 'width' in v_stream and 'height' in v_stream:
                        summary += f"📺 **Resolution:** {v_stream['width']}x{v_stream['height']}\n"
                    if 'codec' in v_stream:
                        summary += f"🎬 **Video Codec:** {v_stream['codec']}\n"
                
                audio_streams = format_data.get('audio_streams', [])
                if audio_streams:
                    summary += f"🔊 **Audio Streams:** {len(audio_streams)}\n"
            
            elif file_type == 'image':
                if 'width' in format_data and 'height' in format_data:
                    summary += f"📐 **Dimensions:** {format_data['width']}x{format_data['height']}\n"
                if 'format' in format_data:
                    summary += f"🖼️ **Format:** {format_data['format']}\n"
                if 'mode' in format_data:
                    summary += f"🎨 **Color Mode:** {format_data['mode']}\n"
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating metadata summary: {e}")
            return "❌ Failed to generate metadata summary"
    
    def supports_metadata_editing(self, file_path: str) -> bool:
        """Check if metadata editing is supported for this file"""
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # Currently support audio files with mutagen
        return MUTAGEN_AVAILABLE and file_ext in self.supported_formats['audio']
    
    def get_editable_fields(self, file_path: str) -> List[str]:
        """Get list of metadata fields that can be edited"""
        if not self.supports_metadata_editing(file_path):
            return []
        
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext in self.supported_formats['audio']:
            return ['title', 'artist', 'album', 'date', 'genre', 'albumartist', 'track']
        
        return []
