from typing import Callable
from typing import Dict
from typing import List
from typing import Optional

class HTMLDocument:
	
	_text: str
	_strict: bool
	_comments: bool

	_rootList: List["HTMLNode"]
	_doctype: Optional["HTMLElementNode"]
	_html: Optional["HTMLElementNode"]
	_head: Optional["HTMLElementNode"]
	_body: Optional["HTMLElementNode"]

	_alwaysSelfClosing: List[str] = [
		"!doctype",
		"meta",
		"input",
		"br",
		"img"
	]
	

	def __init__(self, html: str, strict: bool = False, comments: bool = False):
		self._text = html
		self._strict = strict
		self._comments = comments

		self._doctype = None
		self._html = None
		self._rootList = []
		self._head = None
		self._body = None

		if not self._load(html):
			raise Exception("An error occurred while attempting to read the html document.")

	@property
	def text(self) -> str:
		return self._text
	
	@property
	def strict(self) -> bool:
		return self._strict
	
	@property
	def comments(self) -> bool:
		return self._comments
	
	@property
	def rootList(self) -> List["HTMLElementNode"]:
		return self._rootList

	@property
	def doctype(self) -> Optional["HTMLElementNode"]:
		return self._doctype
	
	@property
	def html(self) -> Optional["HTMLElementNode"]:
		return self._html
	
	@property
	def head(self) -> Optional["HTMLElementNode"]:
		return self._head
	
	@property
	def body(self) -> Optional["HTMLElementNode"]:
		return self._body
	
	@property
	def tables(self) -> Optional[List["HTMLTable"]]:
		if self._body is not None:
			return self._body.tables
		else:
			return None
	
	def _load(self, html: str) -> bool:
		segment: HTMLParserSegment
		node: HTMLElementNode
		response: Optional[HTMLParserSegment]

		parser: HTMLParser = HTMLParser(html, self._strict)

		while (segment := parser.next()) is not None:
			if isinstance(segment, HTMLParserElementSegment):
				if segment.open:
					node = self._createNode(segment)
					self._rootList.append(node)

					# If the tag is not self closing, we need to apply any children.
					if not segment.close and segment.name not in self._alwaysSelfClosing:
						response = self._loadChildren(node, parser)

						# If we got a response here, we have a close tag with no match anywhere in the tree.
						if response is not None and self._strict:
							raise Exception("A close tag was found that has no matching open at position: " + str(segment.start))

				elif self._strict:
					raise Exception("A closing tag was found at the root level of the document at position: " + str(segment.start))

			elif isinstance(segment, HTMLParserTextSegment):
				self._rootList.append(self._createNode(segment))
			elif isinstance(segment, HTMLParserCommentSegment) and self._comments:
				self._rootList.append(self._createNode(segment))
			else:
				raise Exception("Unknown node type.")
				
		self._linkNodes()

		return True
				
	def _loadChildren(self, parent: "HTMLElementNode", parser: "HTMLParser") -> Optional["HTMLParserSegment"]:
		segment: Optional[HTMLParser]
		node: Optional[HTMLElementNode]
		response: Optional[HTMLParserSegment]

		while (segment := parser.next()) is not None:
			if isinstance(segment, HTMLParserElementSegment):

				if segment.open:
					node = self._createNode(segment, parent)
					parent.children.append(node)

					# If the tag is not self closing, we need to apply any children.
					if not segment.close and segment.name not in self._alwaysSelfClosing:
						response = self._loadChildren(node, parser)

						# If we get a response back, it means we got a close tag that wasn't resolved one or more descendent levels down.
						if response is not None:
							# Check if the segment's tag name matches this parent's.
							if segment.name == parent.name:
								# It matched. The parent is now closed and we can go up a level cleanly.
								return None
							else:
								# It did not match. We need to kick the problem up the tree.
								return segment


				elif segment.close:
					# Check if the segment's tag name matches this parent's.
					if segment.name == parent.name:
						# It matched. The parent is now closed and we can go up a level cleanly.
						return None
					else:
						# It did not match. We need to kick the problem up the tree.
						return segment

				else:
					# An element node should always be either or both of an open and a close.
					if self._strict:
						raise Exception("An unidentified tag was found at position: " + str(segment.start))

			elif isinstance(segment, HTMLParserTextSegment):
				parent.children.append(self._createNode(segment, parent))
			elif isinstance(segment, HTMLParserCommentSegment) and self._comments:
				parent.children.append(self._createNode(segment, parent))
			else:
				raise Exception("Unknown node type.")

		# If we got here, we prematurely ran out of html.
		if self._strict:
			raise Exception("HTML ended before all tags were closed.")
		else:
			return None
		
	def _linkNodes(self) -> None:
		# Link the top level nodes.
		for index, node in enumerate(self._rootList):
			if isinstance(node, HTMLElementNode):
				if node.name == "!doctype":
					if index == 0 or not self._strict:
						self._doctype = node

				elif node.name == "html":
					if index in [0, 1] or not self._strict:
						self._html = node

		# If we found a html node, link the head and body nodes.
		if self.html is not None:
			for index, node in enumerate(self.html.children):
				if isinstance(node, HTMLElementNode):
					if node.name == "head":
						if index == 0 or not self._strict:
							self._head = node

					elif node.name == "body":
						if index in [0, 1] or not self._strict:
							self._body = node

	def _createNode(self, segment: "HTMLParserSegment", parent: Optional["HTMLElementNode"] = None) -> Optional["HTMLNode"]:
		node: Optional[HTMLNode]

		if isinstance(segment, HTMLParserElementSegment):
			if segment.open:
				node = HTMLElementNode(parent, None, segment.attributes, segment.name)
			else:
				node = None

		elif isinstance(segment, HTMLParserTextSegment):
			node = HTMLTextNode(parent, segment.text)

		elif isinstance(segment, HTMLParserCommentSegment):
			node = HTMLCommentNode(parent, segment.comment)

		else:
			node = None

		return node

class HTMLNode:
	
	parent: Optional["HTMLNode"]

	def __init__(self, parent: Optional["HTMLNode"] = None):
		self.parent = parent

	@property
	def html(self) -> str:
		return ""

class HTMLElementNode(HTMLNode):
	
	_children: List[HTMLNode]
	_attributes: Dict[str, str]

	name: str

	def __init__(self, parent: Optional[HTMLNode] = None, children: Optional[List[HTMLNode]] = None, attributes: Optional[Dict[str, str]] = None, name: str = "html"):
		super().__init__(parent)
		self.name = name
		
		if isinstance(children, list):
			self._children = children
		else:
			self._children = []

		if isinstance(attributes, dict):
			self._attributes = attributes
		else:
			self._attributes = {}

	@property
	def children(self) -> List[HTMLNode]:
		return self._children
	
	@property
	def attributes(self) -> Dict[str, str]:
		return self._attributes
	
	@property
	def html(self) -> str:
		html: str = "<" + self.name

		# Add attributes
		for key, value in self.attributes.items():
			html += " " + key + "=\"" + value + "\""
		
		# Check whether we should make the tag self closing.
		if len(self.children) > 0:
			html += ">" + self.innerHtml + "</" + self.name + ">"
		else:
			html += "/>"

		return html

	@property
	def innerHtml(self) -> str:
		html: str = ""
		for child in self.children:
			html += child.html

		return html
	
	@property
	def tables(self) -> List["HTMLTable"]:
		results: List[HTMLTable] = []
		for table in self.getElementsByTagName("table"):
			results.append(HTMLTable(table))

		return results
	
	def getElementById(self, id: str) -> Optional["HTMLElementNode"]:
		results = self.getElementsById(id)
		if len(results) > 0:
			return results[0]
		else:
			return None
	
	def getElementsByClassName(self, className: str) -> List["HTMLElementNode"]:
		def filter(node: HTMLNode) -> bool:
			return isinstance(node, HTMLElementNode) and node.hasClass(className)
		
		return self.search(filter)
	
	def getElementsById(self, id: str) -> List["HTMLElementNode"]:
		def filter(node: HTMLNode) -> bool:
			return isinstance(node, HTMLElementNode) and "id" in node.attributes and node.attributes["id"] == id
		
		return self.search(filter)

	def getElementsByName(self, name: str) -> List["HTMLElementNode"]:
		def filter(node: HTMLNode) -> bool:
			return isinstance(node, HTMLElementNode) and "name" in node.attributes and node.attributes["name"] == name
		
		return self.search(filter)

	def getElementsByTagName(self, tagName: str) -> List["HTMLElementNode"]:
		def filter(node: HTMLNode) -> bool:
			return isinstance(node, HTMLElementNode) and node.name == tagName
	
		return self.search(filter)
	
	def hasClass(self, className: str) -> bool:
		if "class" in self.attributes:
			classList: List[str] = self.attributes["class"].split(" ")
			return className in classList
		else:
			return False

	def search(self, filter: Callable[[HTMLNode], bool], maxDepth: Optional[int] = None) -> List[HTMLNode]:
		
		def searchRecursive(results: List[HTMLNode], node: HTMLNode, filter: Callable[[HTMLNode], bool], depthRemaining: Optional[int]) -> None:
			if filter(node):
				results.append(node)

			if isinstance(node, HTMLElementNode) and (depthRemaining is None or (depthRemaining := depthRemaining - 1) >= 0):
				for child in node.children:
					searchRecursive(results, child, filter, depthRemaining)
		
		results: List[HTMLNode] = []
		searchRecursive(results, self, filter, maxDepth)

		return results

class HTMLTextNode(HTMLNode):
	
	text: str

	def __init__(self, parent: Optional[HTMLNode] = None, text: str = ""):
		super().__init__(parent)
		self.text = text

	@property
	def html(self) -> str:
		return self.text

class HTMLCommentNode(HTMLNode):
	
	comment: str

	def __init__(self, parent: Optional[HTMLNode] = None, comment: str = ""):
		super().__init__(parent)
		self.comment = comment

	@property
	def html(self) -> str:
		return "<!-- " + self.comment + " -->"

class HTMLTable:
	
	_node: HTMLElementNode
	_head: List["HTMLTableRow"]
	_body: List["HTMLTableRow"]
	_foot: List["HTMLTableRow"]
	_rows: List["HTMLTableRow"]

	_nodeChildrenCount: int

	def __init__(self, node: HTMLElementNode):
		self._node = node
		self._head = []
		self._body = []
		self._foot = []
		self._rows = []

		self._nodeChildrenCount = len(node.children)

		# If the table has any children, we need to determine whether we are getting thead/tbody/tfoot or are going straight to tr elements.
		if isinstance(node, HTMLElementNode) and len(node.children) > 0:
			firstChild: HTMLNode = node.children[0]

			row: HTMLTableRow
			
			if isinstance(firstChild, HTMLElementNode) and firstChild.name == "tr":
				for child in node.children:
					if isinstance(child, HTMLElementNode) and child.name == "tr" and len(child.children) > 0:
						firstChild = child.children[0]

						if isinstance(firstChild, HTMLElementNode):
							if firstChild.name == "th":
								row = HTMLTableRow(child)
								self._head.append(row)
								self._rows.append(row)

							elif firstChild.name == "td":
								row = HTMLTableRow(child)
								self._body.append(row)
								self._rows.append(row)

			else:
				child: HTMLNode

				position: int = 0

				# Link rows in thead.
				if position < self._nodeChildrenCount and isinstance(child := self._node.children[position], HTMLElementNode) and child.name == "thead":
					for grandchild in child.children:
						if isinstance(grandchild, HTMLElementNode) and grandchild.name == "tr":
							row = HTMLTableRow(grandchild)
							self._head.append(row)
							self._rows.append(row)
					position += 1

				# Link rows in tbody.
				if position < self._nodeChildrenCount and isinstance(child := self._node.children[position], HTMLElementNode) and child.name == "tbody":
					for grandchild in child.children:
						if isinstance(grandchild, HTMLElementNode) and grandchild.name == "tr":
							row = HTMLTableRow(grandchild)
							self._body.append(row)
							self._rows.append(row)
					position += 1

				# Link rows in tfoot.
				if position < self._nodeChildrenCount and isinstance(child := self._node.children[position], HTMLElementNode) and child.name == "tfoot":
					for grandchild in child.children:
						if isinstance(grandchild, HTMLElementNode) and grandchild.name == "tr":
							row = HTMLTableRow(grandchild)
							self._foot.append(row)
							self._rows.append(row)
					position += 1

	@property
	def node(self) -> HTMLElementNode:
		return self._node
	
	@property
	def head(self) -> List["HTMLTableRow"]:
		return self._head
	
	@property
	def body(self) -> List["HTMLTableRow"]:
		return self._body
	
	@property
	def foot(self) -> List["HTMLTableRow"]:
		return self._foot
	
	@property
	def rows(self) -> List["HTMLTableRow"]:
		return self._rows


class HTMLTableRow:

	_node: HTMLElementNode
	_cells: List["HTMLTableCell"]

	def __init__(self, node: HTMLElementNode):
		self._node = node
		self._cells = []

		for child in node.children:
			if isinstance(child, HTMLElementNode) and child.name in ["th", "td"]:
				self._cells.append(HTMLTableCell(child))

	@property
	def node(self) -> HTMLElementNode:
		return self._node
	
	@property
	def cells(self) -> List["HTMLTableCell"]:
		return self._cells

class HTMLTableCell:

	_node: HTMLElementNode

	def __init__(self, node: HTMLElementNode):
		self._node = node

	@property
	def node(self) -> HTMLElementNode:
		return self._node

	@property
	def text(self) -> str:
		return self._node.innerHtml
	
	@property
	def children(self) -> List[HTMLNode]:
		return self._node.children

class HTMLParser:

	_html: str
	_strict: bool

	_position: int
	_segmentCurrent: Optional["HTMLParserSegment"]
	_segmentNext: Optional["HTMLParserSegment"]

	_htmlLength: int

	_contextSwitchTags: List[str] = [
		"script",
		"style",
		"block"
	]

	def __init__(self, html: str, strict: bool = False):
		self._html = html
		self._strict = strict

		self._position = 0
		self._segmentCurrent = None
		self._segmentNext = None

		self._htmlLength = len(html)

	def __iter__(self) -> "HTMLParser":
		return self

	def __next__(self) -> "HTMLParserSegment":
		segment: HTMLParserSegment = self.next()
		if segment == None:
			raise StopIteration
		else:
			return segment

	@property
	def html(self) -> str:
		return self._html
	
	@property
	def strict(self) -> bool:
		return self._strict
	
	@property
	def current(self) -> Optional["HTMLParserSegment"]:
		return self._segmentCurrent
	
	def next(self) -> Optional["HTMLParserSegment"]:
		segment: Optional[HTMLParserSegment]

		segmentCurrent: Optional[HTMLParserSegment] = self._segmentCurrent

		self._position = self._readWhitespace(self._position)
		if self._position == self._htmlLength:
			return None

		# Check for a cached segment.
		if (segment := self._segmentNext) is not None:
			self._segmentNext = None

		# Check if we're in a special context tag.
		elif segmentCurrent is not None and isinstance(segmentCurrent, HTMLParserElementSegment) and not segmentCurrent.close and segmentCurrent.name in self._contextSwitchTags:
			if (segment := self._readSpecialContextTagEnd(self._position, segmentCurrent.name)) is None and (segment := self._readSpecialContextText(self._position, segmentCurrent.name)) is None:
				return None

		# Check for an uncached segment.
		elif (segment := self._readComment(self._position)) is None and (segment := self._readTag(self._position)) is None and (segment := self._readText(self._position)) is None:
			if self._position == self._htmlLength:
				return None
			else:
				raise Exception("Could not read a node, text node or comment at position " + str(self._position) + " in the string.")

		# Update parser location and state.
		self._segmentCurrent = segment
		self._position = segment.end
		
		return segment





	"""
		Parsing Main Methods
	"""
	
	def _readTag(self, position: int) -> Optional["HTMLParserElementSegment"]:
		segment: HTMLParserElementSegment = HTMLParserElementSegment()
		segment.start = position

		result: Optional[int]

		# Check for opening angle bracket.
		if self._html[position] == "<":
			position += 1
		else:
			return None
		
		# Check if the tag is marked as a close tag.
		if self._html[position] == "/":
			position += 1
			segment.open = False
			segment.close = True
		else:
			segment.open = True
			segment.close = False
		
		# Check for spaces before the tag name.
		if not self._strict:
			position = self._readWhitespace(position)

		# Read the tag name.
		result = self._readTagName(position)
		if result is not None:
			segment.name = self._unwrap(self._html[position:result]).lower()
			position = result
		else:
			return None
		
		# Read all attributes.
		position = self._readWhitespace(position)
		while (result := self._readTagAttribute(position, segment.attributes)) is not None:
			position = self._readWhitespace(result)

		# Close tags should not have any attributes.
		if not segment.open and len(segment.attributes) > 0:
			return None
		
		# Check for a self-closing tag.
		if self._html[position] == "/":
			if self._strict and segment.close:
				return None
			else:
				segment.close = True
				position += 1

		# Check for a space between the end slash and the closing angle bracket.
		if not self._strict:
			position = self._readWhitespace(position)

		# Check for an angle bracket.
		if self._html[position] == ">":
			segment.end = position + 1
			segment.text = self._html[segment.start:segment.end]
		else:
			return None

		return segment

	def _readComment(self, position: int) -> Optional["HTMLParserCommentSegment"]:
		segment: HTMLParserCommentSegment = HTMLParserCommentSegment()
		segment.start = position

		# Check for the start of a comment.
		if self._html[position:position + 4] == "<!--":
			position += 4
		else:
			return None

		# check for the end of the comment.
		find: int = self._html.find("-->", position)
		if find >= 0:
			segment.end = find + 3
			segment.text = self._html[segment.start:segment.end]
			segment.comment = segment.text[4:find].strip()
		else:
			return None
		
		return segment

	def _readText(self, position: int) -> Optional["HTMLParserTextSegment"]:
		segment: HTMLParserTextSegment = HTMLParserTextSegment()
		segment.start = position

		# Look for a text element or a comment to terminate the text node.
		while (position := self._html.find("<", position)) >= 0:
			segmentNext: Optional[HTMLParserSegment]

			# Check for a comment or a tag (in that order).
			if (segmentNext := self._readComment(position)) is not None or (segmentNext := self._readTag(position)) is not None:
				self._segmentNext = segmentNext

				segment.end = segmentNext.start
				segment.text = self._html[segment.start:segment.end].strip()
				return segment

			else:
				position += 1

		# This text node is the end of the file. This should not normally be possible.
		if not self._strict:
			segment.end = self._htmlLength
			segment.text = self._html[segment.start:segment.end].strip()
			return segment
		else:
			return None
		
	def _readSpecialContextTagEnd(self, position: int, contextTag: str) -> Optional["HTMLParserElementSegment"]:
		segment: Optional[HTMLParserElementSegment] = self._readTag(position)
		if segment is not None and not segment.open and segment.close and segment.name == contextTag:
			return segment
		else:
			return None

	def _readSpecialContextText(self, position: int, contextTag: str) -> Optional["HTMLParserTextSegment"]:
		segment: HTMLParserTextSegment = HTMLParserTextSegment()
		segment.start = position

		# Look for a text element or a comment to terminate the text node.
		while (position := self._html.find("<", position)) >= 0:
			segmentNext: Optional[HTMLParserSegment]

			# Check for a comment or a tag (in that order).
			if (segmentNext := self._readSpecialContextTagEnd(position, contextTag)) is not None:
				self._segmentNext = segmentNext

				segment.end = segmentNext.start
				segment.text = self._html[segment.start:segment.end].strip()
				return segment
			else:
				position += 1

		# This text node is the end of the file. This should not normally be possible.
		if not self._strict:
			segment.end = self._htmlLength
			segment.text = self._html[segment.start:segment.end].strip()
			return segment
		else:
			return None


	"""
		Parsing Utility Methods
	"""

	def _readTagAttribute(self, position: int, attributes: Dict[str, str]) -> Optional[int]:
		start: int = position

		name: Optional[str] = None
		value: Optional[str] = None
		result: Optional[int] = None

		# Read a property name.
		position = self._readWhitespace(position)
		result = self._readTagAttributeProperty(position)
		if result is not None:
			name = self._unwrap(self._html[position:result]).strip().lower()
			position = result
		else:
			return None
		
		position = self._readWhitespace(position)
		if self._html[position] == "=":
			position += 1

			result = self._readTagAttributeValue(position)
			if result is not None:
				value = self._unwrap(self._html[position:result])
				position = result
			else:
				return None

		else:
			value = "true"

		if self._strict and name in attributes:
			return None
		
		attributes[name] = value

		return position

	def _readTagAttributeProperty(self, position: int) -> Optional[int]:
		start: int = position

		# HTML elements should not have a quoted attribute name.
		if self._strict and self._html[position] in ["\"", "'"]:
			return None
		
		# Deal with quoted attribute names and non-quoted attribute names separately.
		if self._html[position] in ["\"", "'"]:
			quote: str = self._html[position]
			position += 1

			matched: bool = False
			while position < self._htmlLength:
				char: str = self._html[position]

				if char == quote:
					matched = True
					position += 1
					break
				elif char == "\\":
					position += 2
				else:
					position += 1

			if matched:
				return position
			else:
				return None

		else:
			while position < self._htmlLength:
				char: str = self._html[position]

				if char.isspace() or char in ["=", "/", ">"]:
					break
				elif self._strict and not char.isalnum and char not in ["-", "_", "."]:
					return None
				
				position += 1

			if position > start:
				return position
			else:
				return None

	def _readTagAttributeValue(self, position: int) -> Optional[int]:
		start: int = position

		if self._html[position] in ["\"", "'"]:
			quote: str = self._html[position]
			position += 1

			matched: bool = False
			while position < self._htmlLength:
				char: str = self._html[position]

				if char == quote:
					matched = True
					position += 1
					break
				elif char == "\\":
					position += 2
				else:
					position += 1

			if matched:
				return position
			else:
				return None

		elif not self._strict:
			while position < self._htmlLength:
				char: str = self._html[position]

				if char.isspace() or char in ["/", ">"]:
					break

				position += 1

			return position

		else:
			return None

	def _readTagName(self, position: int) -> Optional[int]:
		start: int = position

		# Check for the exceptional case of the doctype tag.
		result: Optional[int] = self._readTagNameDoctype(position)
		if result is not None:
			return result

		while position < self._htmlLength:
			char: str = self._html[position]

			if char.isspace() or char in ["/", ">"]:
				break

			elif self._strict:
				if position == start:
					if not char.isalpha() and char not in ["_"]:
						return None
				else:
					if not char.isalnum() and char not in ["-", "_", "."]:
						return None

			position += 1

		if position > start:
			return position
		else:
			return None

	def _readTagNameDoctype(self, position: int) -> Optional[int]:
		doctype: str = "!DOCTYPE"
		end: int = position + len(doctype)

		if end < self._htmlLength and (self._html[position:end] == doctype or (not self._strict and self._html[position:end].upper() == doctype)):
			char: str = self._html[end]
			if char.isspace() or char in ["/", ">"]:
				return end
			else:
				return None

		else:
			return None

	def _readWhitespace(self, position: int) -> int:
		while position < self._htmlLength and self._html[position].isspace():
			position += 1

		return position
	
	def _unwrap(self, text: str) -> str:
		if text.startswith("\"") or text.startswith("'"):
			return text[1:len(text)-1]
		else:
			return text
	
class HTMLParserSegment:

	text: str
	start: int
	end: int

	def __init__(self, text: str = "", start: int = 0, end: int = 0):
		self.text = text
		self.start = start
		self.end = end

class HTMLParserElementSegment(HTMLParserSegment):

	name: str
	attributes: Dict[str, str]
	open: bool
	close: bool

	def __init__(self, text: str = "", start: int = 0, end: int = 0, name: str = "", open: bool = False, close: bool = False, attributes: Optional[Dict[str, str]] = None):
		super().__init__(text, start, end)
		self.name = name
		self.open = open
		self.close = close

		if isinstance(attributes, dict):
			self.attributes = attributes
		else:
			self.attributes = {}

class HTMLParserTextSegment(HTMLParserSegment):
	pass

class HTMLParserCommentSegment(HTMLParserSegment):
	
	comment: str

	def __init__(self, text: str = "", start: int = 0, end: int = 0, comment: str = ""):
		super().__init__(text, start, end)
		self.comment = comment