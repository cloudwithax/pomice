class AppleMusicRequestException(Exception):
    """An error occurred when making a request to the Apple Music API"""
    pass


class InvalidAppleMusicURL(Exception):
    """An invalid Apple Music URL was passed"""
    pass
