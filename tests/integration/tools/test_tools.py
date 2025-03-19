def test_toolsgroups_unregister(llama_stack_client):
    client = llama_stack_client
    client.toolgroups.unregister(
        toolgroup_id="builtin::websearch",
    )
