from Data_Grabber import DataGrabber


class Parser:

    def __init__(self, file):
        self.data_grabber = DataGrabber()
        self.file = open(file)
        self.file_list = self.file.readlines()
        self.header_list = []
        self.dict = {}  # {key: header { value: key, value}}

    def getData(self):
        current_header = ''
        for line in self.file_list:
            if line.__contains__('[') and line.__contains__(']'):  # headers
                current_header = self.data_grabber.getHeader(line)
            else:  # key value pairs
                key = self.data_grabber.getKey(line)
                if key != '' and key != ';':
                    val = self.data_grabber.getContents(line)
                    self.dict.setdefault(current_header, {})
                    self.dict[current_header][key] = val
        return self.dict


# gets the index value of desired header
# could be optimized to include a starting index
# to improve efficiency for headers near the bottom of the list
def getIndex(file_list, goal):
    for i, s in enumerate(file_list):
        if s.__contains__(goal):
            return i
    return -1
