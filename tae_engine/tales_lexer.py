"""Custom lexer for the TALES language."""
import re
from enum import Enum, auto
from typing import Optional, List, Tuple, Dict

# Token types Enum
class TokenType(Enum):
    UNKNOWN = auto()
    SCENE = auto()
    DIALOGUE = auto()
    CHOICE = auto()
    SEPARATOR = auto()
    TRANSITION = auto()
    TEXT = auto()
    COMPARATOR = auto()
    NUMBER = auto()
    BOOLEAN = auto()
    IF = auto()
    ELSE = auto()
    ENDIF = auto()
    OPEN_BRACKET = auto()
    CLOSE_BRACKET = auto()
    
    __repr__ = lambda self: self.name
    

class TalesLexer():
    DIRECTIVE_RE = re.compile(r"@([a-zA-Z_][a-zA-Z0-9_]*)")
    NUMBER_RE = re.compile(r"^[\+\-]?\d+(\.\d+)?$")
    COMPARATOR_RE = re.compile(r"^(==|!=|<=|>=|<|>)$")
    BOOLEAN_RE = re.compile(r"^(true|false)$")
    
     
    @staticmethod
    def create_token(token_type: TokenType, value: str) -> Tuple[TokenType, str]:
        """Create a token, converting the value if necessary."""
        if token_type == TokenType.TEXT and value.lower() in ["true", "false"]:
            return (TokenType.BOOLEAN, value.lower())
        return (token_type, value)
        
    @staticmethod
    def _look_ahead(
        line: str, pos: int, length: int = 1
    ) -> Optional[str]:
        """Safely look ahead in the string."""
        if pos + length <= len(line):
            return line[pos : pos + length]
        return None
    
    @staticmethod
    def _skip_whitespace(line: str, pos: int) -> int:
        """Skip whitespace characters."""
        while pos < len(line) and line[pos].isspace():
            pos += 1
        return pos
        
    @staticmethod
    def tokenize(text: str) -> Dict[int, List[Tuple[TokenType, str]]]:
        """Tokenize a TALES script."""
        lines = text.splitlines()
        all_tokens = {}
        for line_num, line in enumerate(lines, 1):
            try:
                line_tokens = TalesLexer.tokenize_line(line)
                if line_tokens:
                    all_tokens[line_num] = line_tokens
            except Exception as e:
                raise ValueError(
                    f"Lexer Error on line {line_num}: {e}\n-> {line}"
                ) from e
        return all_tokens
    
    @staticmethod
    def _handle_directives(line: str, pos: int) -> Tuple[int, Tuple[TokenType, str]]:
        directive_token: Optional[Tuple[TokenType, str]] = None
        directive_len = 0
        
        if TalesLexer._look_ahead(line, pos, len("@scene")) == "@scene":
            directive_token = (TokenType.SCENE, "@scene")
            directive_len = len("@scene")
        elif TalesLexer._look_ahead(line, pos, len("@if")) == "@if":
            directive_token = (TokenType.IF, "@if")
            directive_len = len("@if")
        elif TalesLexer._look_ahead(line, pos, len("@else")) == "@else":
            directive_token = (TokenType.ELSE, "@else")
            directive_len = len("@else")
        elif TalesLexer._look_ahead(line, pos, len("@endif")) == "@endif":
            directive_token = (TokenType.ENDIF, "@endif")
            directive_len = len("@endif")
        else:
            # Try to identify the unknown directive for error reporting
            # Match until whitespace or end of line
            match = TalesLexer.DIRECTIVE_RE.match(line, pos)
            if match:
                raise ValueError(
                    f"Unknown directive '{match.group(1)}' at position {pos}."
                )
            else:
                raise ValueError(
                    f"Invalid directive at position {pos}."
                )
                
        # Move past the directive
        pos += directive_len
        
        # Only whitespace or end of line (pos == len(line)) is allowed directly after the directive
        if pos < len(line) and line[pos].isspace():
            pos = TalesLexer._skip_whitespace(line, pos)
        elif pos >= len(line):
            pass
        else:
            raise ValueError(
                f"Unexpected character after directive {directive_token[1]} at position {pos}."
            )
            
        return pos, directive_token

    @staticmethod
    def _handle_separator(line: str, pos: int) -> Tuple[int, Tuple[TokenType, str]]:
        """Handle a separator token."""
        # Skip whitespace after the separator
        pos = TalesLexer._skip_whitespace(line, pos + 1)
        
        return pos, (TokenType.SEPARATOR, ":")
    
    @staticmethod
    def _handle_bracket(line: str, pos: int) -> Tuple[int, Tuple[TokenType, str]]:
        """Handle a bracket token."""
        current_char = line[pos]
        if current_char == "{":
            token_type = TokenType.OPEN_BRACKET
        elif current_char == "}":
            token_type = TokenType.CLOSE_BRACKET
        else:
            raise ValueError(
                f"Unexpected character '{current_char}' at position {pos}."
            )
        
        # Skip whitespace after the bracket
        pos = TalesLexer._skip_whitespace(line, pos + 1)
        
        return pos, (token_type, current_char)
    
    @staticmethod
    def _handle_dialogue(line: str, pos: int) -> Tuple[int, Tuple[TokenType, str]]:
        """Handle a dialogue token."""
        # There has to be at least one whitespace after the dialogue
        if pos + 1 >= len(line) or not line[pos + 1].isspace():
            raise ValueError(
                f"Missing whitespace after dialogue '>' at position {pos}."
            )
        
        # Skip remaining whitespace
        pos = TalesLexer._skip_whitespace(line, pos + 2)
        
        return pos, (TokenType.DIALOGUE, ">")
    
    @staticmethod
    def _handle_choice(line: str, pos: int) -> Tuple[int, Tuple[TokenType, str]]:
        """Handle a choice token."""
        # Check how many asterisks are there
        asterisks = 1
        while pos + asterisks < len(line) and line[pos + asterisks] == "*":
            asterisks += 1
            
        # Skip whitespace after the asterisks
        pos = TalesLexer._skip_whitespace(line, pos + asterisks)
        
        return pos, (TokenType.CHOICE, "*" * asterisks)
    
    @staticmethod
    def _handle_transition(line: str, pos: int) -> Tuple[int, Tuple[TokenType, str]]:
        """Handle a transition token."""
        # There has to be at least one whitespace after the transition
        if pos + 2 >= len(line) or not line[pos + 2].isspace():
            raise ValueError(
                f"Missing whitespace after transition '->' at position {pos}."
            )
            
        # Skip remaining whitespace
        pos = TalesLexer._skip_whitespace(line, pos + 2)
        
        return pos, (TokenType.TRANSITION, "->")
    
    @staticmethod
    def tokenize_line(line: str) -> List[Tuple[TokenType, str]]:
        tokens: List[Tuple[TokenType, str]] = []
        pos = 0
        line_len = len(line)
        text = ""
        
        def add_text_token(text, tokens) -> str:
            if text:
                # remove leading and trailing whitespace
                text = text.strip()
                
                # Check if the text is a number or boolean
                if TalesLexer.NUMBER_RE.match(text):
                    tokens.append(TalesLexer.create_token(TokenType.NUMBER, text))
                elif TalesLexer.BOOLEAN_RE.match(text):
                    tokens.append(TalesLexer.create_token(TokenType.BOOLEAN, text))
                elif TalesLexer.COMPARATOR_RE.match(text):
                    tokens.append(TalesLexer.create_token(TokenType.COMPARATOR, text))
                else:
                    tokens.append(TalesLexer.create_token(TokenType.TEXT, text))
                text = ""
            return text
        
        # --- Preprocessing: Skip whitespace and comments ---
        initial_pos = TalesLexer._skip_whitespace(line, pos)
        pos = initial_pos
        if pos == line_len or TalesLexer._look_ahead(line, pos, 2) == "//":
            return []
        
        # --- Main Tokenization Loop ---
        while pos < line_len:
            current_char = line[pos]
            
            if pos == initial_pos:
                if current_char == "@":
                    pos, token = TalesLexer._handle_directives(line, pos)
                    if token:
                        tokens.append(token)
                        
                elif current_char == ">":
                    pos, token = TalesLexer._handle_dialogue(line, pos)
                    if token:
                        tokens.append(token)
                        
                elif current_char == "*":
                    pos, token = TalesLexer._handle_choice(line, pos)
                    if token:
                        tokens.append(token)
                else:
                    raise ValueError(
                        f"Unexpected token at beginning of line: '{current_char}' at position {pos}."
                    )
                
            else:
                if current_char == ":":
                    text = add_text_token(text, tokens)
                    
                    pos, token = TalesLexer._handle_separator(line, pos)
                    if token:
                        tokens.append(token)
                
                elif current_char in ["{", "}"]:
                    text = add_text_token(text, tokens)
                    
                    pos, token = TalesLexer._handle_bracket(line, pos)
                    if token:
                        tokens.append(token)
                        
                elif current_char == "-" and TalesLexer._look_ahead(line, pos, 2) == "->":
                    text = add_text_token(text, tokens)
                    
                    pos, token = TalesLexer._handle_transition(line, pos)
                    if token:
                        tokens.append(token)
                
                elif current_char == "/" and TalesLexer._look_ahead(line, pos, 2) == "//":
                    # Skip the comment
                    pos = line_len        
                
                else:
                    text += current_char
                    pos += 1

        text = add_text_token(text, tokens)
        
        return tokens
    
if __name__ == "__main__":
    # read in the file
    filename = "test.tales"
    with open(filename, "r") as file:
        text = file.read()
        
    # tokenize the text
    tokens = TalesLexer.tokenize(text)
    
    for line_num, token_lines in tokens.items():
        print(f"Line {line_num}:", end=" ")
        print(token_lines)
        
    
    # print the tokens
    #print(f"There are {sum([len(token_lines) for token_lines in tokens])} tokens in {filename}:")