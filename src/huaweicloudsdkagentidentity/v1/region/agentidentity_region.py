
from huaweicloudsdkcore.region.provider import RegionProviderChain
from huaweicloudsdkcore.region.region import Region


class AgentIdentityRegion:
    _PROVIDER = RegionProviderChain.get_default_region_provider_chain("AGENTIDENTITY")

    AP_SOUTHEAST_4 = Region("ap-southeast-4",
                        "https://agent-identity.ap-southeast-4.myhuaweicloud.com")

    static_fields = {
        "ap-southeast-4": AP_SOUTHEAST_4,
    }

    @classmethod
    def value_of(cls, region_id, static_fields=None):
        if not region_id:
            msg = "Unexpected empty parameter: region_id"
            raise KeyError(msg)

        fields = static_fields or cls.static_fields

        region = cls._PROVIDER.get_region(region_id)
        if region:
            return region

        if region_id in fields:
            return fields.get(region_id)

        msg = (
            "region_id '{}' is not in the following supported regions of service 'AgentIdentity': [{}]".format(
            region_id, ", ".join(sorted(fields.keys())))
        )
        raise KeyError(msg)
