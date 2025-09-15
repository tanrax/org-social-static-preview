#!/usr/bin/env python3
import os
import re
from datetime import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
import argparse

class OrgSocialParser:
	def __init__(self):
		self.metadata = {}
		self.posts = []

	def parse_file(self, file_path):
		"""Parse the org social file and extract metadata and posts"""
		self.metadata = {}
		self.posts = []

		with open(file_path, 'r', encoding='utf-8') as f:
			content = f.read()

		# Extract global metadata
		self._extract_metadata(content)

		# Extract posts
		self._extract_posts(content)

		return self.posts

	def _extract_metadata(self, content):
		"""Extract global metadata from the org file"""
		metadata_patterns = {
			'TITLE': r'^\s*\#\+TITLE:\s*(.+)$',
			'NICK': r'^\s*\#\+NICK:\s*(.+)$',
			'DESCRIPTION': r'^\s*\#\+DESCRIPTION:\s*(.+)$',
			'AVATAR': r'^\s*\#\+AVATAR:\s*(.+)$',
		}

		for key, pattern in metadata_patterns.items():
			match = re.search(pattern, content, re.MULTILINE)
			if match:
				self.metadata[key] = match.group(1).strip()

	def _extract_posts(self, content):
		"""Extract all posts from the org file"""
		# Find the Posts section
		posts_pattern = r'^\*\s+Posts\s*$'
		posts_section_match = re.search(posts_pattern, content, re.MULTILINE)
		if not posts_section_match:
			print("Posts section not found")
			return

		posts_content = content[posts_section_match.end():]

		# Find all ** headers (posts) - looking for ** at start of line
		post_pattern = r'^(\*\*)\s*$'
		post_positions = []

		for match in re.finditer(post_pattern, posts_content, re.MULTILINE):
			post_positions.append(match.end())

		if not post_positions:
			print("No headers found in Posts section")
			return

		print(f"Found {len(post_positions)} headers")

		# Extract content between ** headers
		for i, start_pos in enumerate(post_positions):
			# Find the end of this post (next ** or end of content)
			if i + 1 < len(post_positions):
				# Find the next ** header
				next_start = post_positions[i + 1]
				# Go back to find the actual ** line
				temp_content = posts_content[:next_start]
				last_newline = temp_content.rfind('\n**')
				if last_newline != -1:
					end_pos = last_newline
				else:
					end_pos = next_start
			else:
				end_pos = len(posts_content)

			block = posts_content[start_pos:end_pos].strip()

			if block:
				post = self._parse_post_block(block)
				if post and post.get('ID'):
					self.posts.append(post)
					print(f"Post added with ID: {post.get('ID')}")

	def _parse_post_block(self, block):
		"""Parse a single post block"""
		post = {}

		# Extract properties
		properties_match = re.search(r':PROPERTIES:\s*\n(.*?)\n:END:', block, re.DOTALL)
		if properties_match:
			properties_content = properties_match.group(1)

			# Parse each property using simple string operations
			for line in properties_content.split('\n'):
				line = line.strip()
				if line and line.startswith(':') and line.count(':') >= 2:
					# Find the second colon
					first_colon = line.find(':', 1)
					if first_colon != -1:
						key = line[1:first_colon].strip()
						value = line[first_colon + 1:].strip()
						if key:
							post[key] = value

		# Extract post content (everything after :END:)
		end_match = re.search(r':END:\s*\n', block)
		if end_match:
			content = block[end_match.end():].strip()
			post['content'] = content
		else:
			# No properties block, entire block is content
			post['content'] = block

		return post

class PreviewGenerator:
	def __init__(self, template_dir=".", template_name="template.html"):
		self.env = Environment(loader=FileSystemLoader(template_dir))
		def og_description(value, max_length=120):
			import re
			# Replace newlines with spaces
			text = value.replace('\r\n', ' ').replace('\n', ' ').replace('\r', ' ')
			# Collapse all whitespace to single spaces
			text = re.sub(r'\s+', ' ', text)
			# HTML tag filter
			text = re.sub(r'<[^>]+>', '', text)
			# Collapse multiple spaces
			text = re.sub(r' +', ' ', text)
			if len(text) > max_length:
				text = text[:max_length].rstrip() + '...'
			return text.strip()
		self.env.filters['og_description'] = og_description
		self.template = self.env.get_template(template_name)

	def generate_preview(self, post, metadata):
		"""Generate HTML preview for a single post"""
		feed_url = metadata.get('FEED_URL', '')
		context = self._prepare_context(post, metadata, feed_url)
		return self.template.render(**context)

	def _prepare_context(self, post, metadata, feed_url):
		"""Prepare context data for template rendering"""
		post_id = post.get('ID', '')
		content = post.get('content', '')
		mood = post.get('MOOD', '')
		lang = post.get('LANG', 'es')
		tags = post.get('TAGS', '')
		reply_to = post.get('REPLY_TO', '')
		client = post.get('CLIENT', '')

		formatted_content = self._format_content(content, mood, reply_to)

		nick = metadata.get('NICK', 'User')
		title = metadata.get('TITLE', 'socia.org')
		description = metadata.get('DESCRIPTION', '')
		avatar_url = metadata.get('AVATAR', '')

		formatted_time = self._format_timestamp(post_id)
		tags_list = tags.split() if tags else []

		post_url = f"{feed_url}#{post_id}" if feed_url and post_id else ''

		return {
			'post_id': post_id,
			'content': content,
			'formatted_content': formatted_content,
			'mood': mood,
			'language': lang,
			'tags': tags_list,
			'tags_string': tags,
			'reply_to': reply_to,
			'client': client,
			'is_reply': bool(reply_to),
			'has_mood': bool(mood),
			'has_tags': bool(tags),
			'has_content': bool(content.strip()),
			'nick': nick,
			'title': title,
			'description': description,
			'avatar_url': avatar_url,
			'has_avatar': bool(avatar_url),
			'user_initial': nick[0].upper() if nick else 'U',
			'formatted_time': formatted_time,
			'timestamp': post_id,
			'post_url': post_url,
		}

	def _format_content(self, content, mood, reply_to):
		"""Format post content"""
		if not content.strip() and mood:
			return f'<span style="font-size: 20px;">{mood}</span>'

		formatted = content

		# Handle org-social mentions
		formatted = re.sub(
			r'\[\[org-social:([^\]]+)\]\[([^\]]+)\]\]',
			r'<a href="#" style="color: #1d9bf0;">@\2</a>',
			formatted
		)

		# Handle regular links
		formatted = re.sub(
			r'\[\[([^\]]+)\]\[([^\]]+)\]\]',
			r'<a href="\1" style="color: #1d9bf0;" target="_blank">\2</a>',
			formatted
		)

		# Handle simple URLs
		formatted = re.sub(
			r'\[\[([^\]]+)\]\]',
			r'<a href="\1" style="color: #1d9bf0;" target="_blank">\1</a>',
			formatted
		)

		# Convert line breaks
		formatted = formatted.replace('\n', '<br>')

		# Add mood emoji if present and there's content
		if mood and content.strip():
			formatted = f'{formatted} <span style="font-size: 16px;">{mood}</span>'

		return formatted or 'No content'

	def _format_timestamp(self, timestamp):
		"""Format timestamp for display"""
		try:
			dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
			now = datetime.now(dt.tzinfo)

			diff = now - dt

			if diff.days > 0:
				return f'{diff.days}d'
			elif diff.seconds > 3600:
				return f'{diff.seconds // 3600}h'
			else:
				return f'{max(1, diff.seconds // 60)}min'
		except:
			return '1h'

class OrgSocialPreviewGenerator:
	def __init__(self, social_file, preview_dir, template_dir=".", template_name="template.html"):
		self.social_file = Path(social_file).resolve()
		self.preview_dir = Path(preview_dir)
		self.parser = OrgSocialParser()
		self.generator = PreviewGenerator(template_dir, template_name)

		# Create preview directory if it doesn't exist
		self.preview_dir.mkdir(exist_ok=True)

	def generate_all_previews(self):
		"""Generate all preview files"""
		try:
			# Clear existing HTML files
			print(f"Cleaning existing HTML files...")
			deleted_count = 0
			for existing_file in self.preview_dir.glob("*.html"):
				existing_file.unlink()
				deleted_count += 1
			print(f"Deleted {deleted_count} files")

			# Parse posts
			posts = self.parser.parse_file(self.social_file)
			print(f"Processed {len(posts)} posts")

			# Generate new previews
			generated_count = 0
			for post in posts:
				post_id = post.get('ID', '')
				if not post_id:
					continue

				# Generate safe filename from ID
				safe_filename = post_id.replace(':', '-').replace('+', 'plus')
				preview_path = self.preview_dir / f"{safe_filename}.html"

				html = self.generator.generate_preview(post, self.parser.metadata)

				with open(preview_path, 'w', encoding='utf-8') as f:
					f.write(html)

				print(f"Generated: {preview_path.name}")
				generated_count += 1

			print(f"Completed: {generated_count} files generated")

		except Exception as e:
			print(f"Error: {e}")
			import traceback
			traceback.print_exc()
			return 1

		return 0

def main():
	parser = argparse.ArgumentParser(description='Generate HTML previews for Org Social posts')
	parser.add_argument('--social-file', '-s', default='social.org')
	parser.add_argument('--preview-dir', '-p', default='preview')
	parser.add_argument('--template-dir', '-td', default='.')
	parser.add_argument('--template-name', '-tn', default='template.html')

	args = parser.parse_args()

	# Verify files exist
	if not Path(args.social_file).exists():
		print(f"Error: {args.social_file} not found")
		return 1

	template_path = Path(args.template_dir) / args.template_name
	if not template_path.exists():
		print(f"Error: {template_path} not found")
		return 1

	# Create generator and run
	generator = OrgSocialPreviewGenerator(
		args.social_file,
		args.preview_dir,
		args.template_dir,
		args.template_name
	)

	return generator.generate_all_previews()

if __name__ == '__main__':
	exit(main())
