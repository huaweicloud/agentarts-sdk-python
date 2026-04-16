
from huaweicloudsdkcore.utils.http_utils import sanitize_for_serialization


class RichAuthorizationDetail:

    """
    Attributes:
      openapi_types (dict): The key is attribute name
                            and the value is attribute type.
      attribute_map (dict): The key is attribute name
                            and the value is json key in definition.
    """
    sensitive_list = []

    openapi_types = {
        "type": "str",
        "actions": "list[str]",
        "locations": "list[str]",
        "identifier": "str",
        "datatypes": "list[str]",
        "privileges": "list[str]",
        "additional_rar_parameters": "dict(str, str)"
    }

    attribute_map = {
        "type": "type",
        "actions": "actions",
        "locations": "locations",
        "identifier": "identifier",
        "datatypes": "datatypes",
        "privileges": "privileges",
        "additional_rar_parameters": "additional_rar_parameters"
    }

    def __init__(self, type=None, actions=None, locations=None, identifier=None, datatypes=None, privileges=None, additional_rar_parameters=None):
        r"""RichAuthorizationDetail

        The model defined in huaweicloud sdk

        :param type: Mandatory RAR type identifier (RFC 9396 §2.1), e.g. payment_initiation, banking_accounts, crm_access, api_invocation
        :type type: str
        :param actions: An array of strings representing the kinds of actions to be taken at the resource
        :type actions: list[str]
        :param locations: An array of strings representing the location of the resource or RS. These strings are typically URIs identifying the location of the RS. This field can allow a client to specify a particular RS
        :type locations: list[str]
        :param identifier: A string identifier indicating a specific resource available at the API
        :type identifier: str
        :param datatypes: An array of strings representing the kinds of data being requested from the resource
        :type datatypes: list[str]
        :param privileges: An array of strings representing the types or levels of privilege being requested at the resource
        :type privileges: list[str]
        :param additional_rar_parameters: Extended custom RAR parameters (per RFC 9396 §3.2) - vendor-specific fine-grained auth metadata, does not conflict with standard OAuth2 params
        :type additional_rar_parameters: dict(str, str)
        """



        self._type = None
        self._actions = None
        self._locations = None
        self._identifier = None
        self._datatypes = None
        self._privileges = None
        self._additional_rar_parameters = None
        self.discriminator = None

        self.type = type
        if actions is not None:
            self.actions = actions
        if locations is not None:
            self.locations = locations
        if identifier is not None:
            self.identifier = identifier
        if datatypes is not None:
            self.datatypes = datatypes
        if privileges is not None:
            self.privileges = privileges
        if additional_rar_parameters is not None:
            self.additional_rar_parameters = additional_rar_parameters

    @property
    def type(self):
        r"""Gets the type of this RichAuthorizationDetail.

        Mandatory RAR type identifier (RFC 9396 §2.1), e.g. payment_initiation, banking_accounts, crm_access, api_invocation

        :return: The type of this RichAuthorizationDetail.
        :rtype: str
        """
        return self._type

    @type.setter
    def type(self, type):
        r"""Sets the type of this RichAuthorizationDetail.

        Mandatory RAR type identifier (RFC 9396 §2.1), e.g. payment_initiation, banking_accounts, crm_access, api_invocation

        :param type: The type of this RichAuthorizationDetail.
        :type type: str
        """
        self._type = type

    @property
    def actions(self):
        r"""Gets the actions of this RichAuthorizationDetail.

        An array of strings representing the kinds of actions to be taken at the resource

        :return: The actions of this RichAuthorizationDetail.
        :rtype: list[str]
        """
        return self._actions

    @actions.setter
    def actions(self, actions):
        r"""Sets the actions of this RichAuthorizationDetail.

        An array of strings representing the kinds of actions to be taken at the resource

        :param actions: The actions of this RichAuthorizationDetail.
        :type actions: list[str]
        """
        self._actions = actions

    @property
    def locations(self):
        r"""Gets the locations of this RichAuthorizationDetail.

        An array of strings representing the location of the resource or RS. These strings are typically URIs identifying the location of the RS. This field can allow a client to specify a particular RS

        :return: The locations of this RichAuthorizationDetail.
        :rtype: list[str]
        """
        return self._locations

    @locations.setter
    def locations(self, locations):
        r"""Sets the locations of this RichAuthorizationDetail.

        An array of strings representing the location of the resource or RS. These strings are typically URIs identifying the location of the RS. This field can allow a client to specify a particular RS

        :param locations: The locations of this RichAuthorizationDetail.
        :type locations: list[str]
        """
        self._locations = locations

    @property
    def identifier(self):
        r"""Gets the identifier of this RichAuthorizationDetail.

        A string identifier indicating a specific resource available at the API

        :return: The identifier of this RichAuthorizationDetail.
        :rtype: str
        """
        return self._identifier

    @identifier.setter
    def identifier(self, identifier):
        r"""Sets the identifier of this RichAuthorizationDetail.

        A string identifier indicating a specific resource available at the API

        :param identifier: The identifier of this RichAuthorizationDetail.
        :type identifier: str
        """
        self._identifier = identifier

    @property
    def datatypes(self):
        r"""Gets the datatypes of this RichAuthorizationDetail.

        An array of strings representing the kinds of data being requested from the resource

        :return: The datatypes of this RichAuthorizationDetail.
        :rtype: list[str]
        """
        return self._datatypes

    @datatypes.setter
    def datatypes(self, datatypes):
        r"""Sets the datatypes of this RichAuthorizationDetail.

        An array of strings representing the kinds of data being requested from the resource

        :param datatypes: The datatypes of this RichAuthorizationDetail.
        :type datatypes: list[str]
        """
        self._datatypes = datatypes

    @property
    def privileges(self):
        r"""Gets the privileges of this RichAuthorizationDetail.

        An array of strings representing the types or levels of privilege being requested at the resource

        :return: The privileges of this RichAuthorizationDetail.
        :rtype: list[str]
        """
        return self._privileges

    @privileges.setter
    def privileges(self, privileges):
        r"""Sets the privileges of this RichAuthorizationDetail.

        An array of strings representing the types or levels of privilege being requested at the resource

        :param privileges: The privileges of this RichAuthorizationDetail.
        :type privileges: list[str]
        """
        self._privileges = privileges

    @property
    def additional_rar_parameters(self):
        r"""Gets the additional_rar_parameters of this RichAuthorizationDetail.

        Extended custom RAR parameters (per RFC 9396 §3.2) - vendor-specific fine-grained auth metadata, does not conflict with standard OAuth2 params

        :return: The additional_rar_parameters of this RichAuthorizationDetail.
        :rtype: dict(str, str)
        """
        return self._additional_rar_parameters

    @additional_rar_parameters.setter
    def additional_rar_parameters(self, additional_rar_parameters):
        r"""Sets the additional_rar_parameters of this RichAuthorizationDetail.

        Extended custom RAR parameters (per RFC 9396 §3.2) - vendor-specific fine-grained auth metadata, does not conflict with standard OAuth2 params

        :param additional_rar_parameters: The additional_rar_parameters of this RichAuthorizationDetail.
        :type additional_rar_parameters: dict(str, str)
        """
        self._additional_rar_parameters = additional_rar_parameters

    def to_dict(self):
        result = {}

        for attr, _ in self.openapi_types.items():
            value = getattr(self, attr)
            if isinstance(value, list):
                result[attr] = [x.to_dict() if hasattr(x, "to_dict") else x for x in value]
            elif hasattr(value, "to_dict"):
                result[attr] = value.to_dict()
            elif isinstance(value, dict):
                result[attr] = dict(map(
                    lambda item: (item[0], item[1].to_dict())
                    if hasattr(item[1], "to_dict") else item,
                    value.items()
                ))
            elif attr in self.sensitive_list:
                result[attr] = "****"
            else:
                result[attr] = value

        return result

    def to_str(self):
        """Returns the string representation of the model"""
        import simplejson as json
        return json.dumps(sanitize_for_serialization(self), ensure_ascii=False)

    def __repr__(self):
        """For `print`"""
        return self.to_str()

    def __eq__(self, other):
        """Returns true if both objects are equal"""
        if not isinstance(other, RichAuthorizationDetail):
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        """Returns true if both objects are not equal"""
        return not self == other
