from agentarts.sdk.runtime.context import AgentArtsRuntimeContext


def test_user_id_context():
    # GIVEN: Initial state (should be None)
    assert AgentArtsRuntimeContext.get_user_id() is None

    # WHEN: Setting user_id
    AgentArtsRuntimeContext.set_user_id("test-user-123")

    # THEN: get_user_id should return the value
    assert AgentArtsRuntimeContext.get_user_id() == "test-user-123"

    # WHEN: Setting it back to None
    AgentArtsRuntimeContext.set_user_id(None)
    assert AgentArtsRuntimeContext.get_user_id() is None


def test_user_token_context():
    # GIVEN: Initial state (should be None)
    assert AgentArtsRuntimeContext.get_user_token() is None

    # WHEN: Setting user_token
    AgentArtsRuntimeContext.set_user_token("test-token-xyz")

    # THEN: get_user_token should return the value
    assert AgentArtsRuntimeContext.get_user_token() == "test-token-xyz"

    # WHEN: Setting it back to None
    AgentArtsRuntimeContext.set_user_token(None)
    assert AgentArtsRuntimeContext.get_user_token() is None


def test_oauth2_custom_state_context():
    # GIVEN: Initial state (should be None)
    assert AgentArtsRuntimeContext.get_oauth2_custom_state() is None

    # WHEN: Setting oauth2_custom_state
    AgentArtsRuntimeContext.set_oauth2_custom_state("test-state")

    # THEN: get_oauth2_custom_state should return the value
    assert AgentArtsRuntimeContext.get_oauth2_custom_state() == "test-state"

    # WHEN: Setting it back to None
    AgentArtsRuntimeContext.set_oauth2_custom_state(None)
    assert AgentArtsRuntimeContext.get_oauth2_custom_state() is None


def test_request_id_context():
    assert AgentArtsRuntimeContext.get_request_id() is None
    AgentArtsRuntimeContext.set_request_id("req-123")
    assert AgentArtsRuntimeContext.get_request_id() == "req-123"
    AgentArtsRuntimeContext.set_request_id(None)
    assert AgentArtsRuntimeContext.get_request_id() is None


def test_session_id_context():
    assert AgentArtsRuntimeContext.get_session_id() is None
    AgentArtsRuntimeContext.set_session_id("sess-123")
    assert AgentArtsRuntimeContext.get_session_id() == "sess-123"
    AgentArtsRuntimeContext.set_session_id(None)
    assert AgentArtsRuntimeContext.get_session_id() is None
