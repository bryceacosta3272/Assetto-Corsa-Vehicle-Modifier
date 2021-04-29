class DataGrabber:

    def getContents(self, line):
        output = ''
        capture = False
        for letter in line:
            if capture and (letter != ';' and letter != '\n'):
                output += letter
            elif letter == '=':
                capture = True
            elif letter == ';' or letter == '\n':
                break

        if capture:
            return self.removeSpaces(output)
        else:
            return output

    def removeSpaces(self, output):
        if len(output) > 0:
            i = len(output) - 1
            while not output[i].isalnum() and i > 0:
                output = output[:i]
                i -= 1

        return output

    def getKey(self, line):
        output = ''
        for letter in line:
            if letter == '=' or letter == ';' or letter == ' ' \
                    or letter == '\t' or letter == '\n' or letter == '':
                break
            else:
                output += letter.replace('\n', '')
        return output

    def getHeader(self, line):
        output = ''
        for letter in line:
            if letter == '\n' or letter == '\t' or letter == ' ' or letter == '':
                break
            else:
                output += letter
        return output
