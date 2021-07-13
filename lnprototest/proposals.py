dual_fund_csv = [
    "msgtype,tx_add_input,66",
    "msgdata,tx_add_input,channel_id,channel_id,",
    "msgdata,tx_add_input,serial_id,u64,",
    "msgdata,tx_add_input,prevtx_len,u16,",
    "msgdata,tx_add_input,prevtx,byte,prevtx_len",
    "msgdata,tx_add_input,prevtx_vout,u32,",
    "msgdata,tx_add_input,sequence,u32,",
    "msgdata,tx_add_input,script_sig_len,u16,",
    "msgdata,tx_add_input,script_sig,byte,script_sig_len",
    "msgtype,tx_add_output,67",
    "msgdata,tx_add_output,channel_id,channel_id,",
    "msgdata,tx_add_output,serial_id,u64,",
    "msgdata,tx_add_output,sats,u64,",
    "msgdata,tx_add_output,scriptlen,u16,",
    "msgdata,tx_add_output,script,byte,scriptlen",
    "msgtype,tx_remove_input,68",
    "msgdata,tx_remove_input,channel_id,channel_id,",
    "msgdata,tx_remove_input,serial_id,u64,",
    "msgtype,tx_remove_output,69",
    "msgdata,tx_remove_output,channel_id,channel_id,",
    "msgdata,tx_remove_output,serial_id,u64,",
    "msgtype,tx_complete,70",
    "msgdata,tx_complete,channel_id,channel_id,",
    "msgtype,tx_signatures,71",
    "msgdata,tx_signatures,channel_id,channel_id,",
    "msgdata,tx_signatures,txid,sha256,",
    "msgdata,tx_signatures,num_witnesses,u16,",
    "msgdata,tx_signatures,witness_stack,witness_stack,num_witnesses",
    "subtype,witness_stack",
    "subtypedata,witness_stack,num_input_witness,u16,",
    "subtypedata,witness_stack,witness_element,witness_element,num_input_witness",
    "subtype,witness_element",
    "subtypedata,witness_element,len,u16,",
    "subtypedata,witness_element,witness,byte,len",
    "msgtype,open_channel2,64",
    "msgdata,open_channel2,chain_hash,chain_hash,",
    "msgdata,open_channel2,channel_id,channel_id,",
    "msgdata,open_channel2,funding_feerate_perkw,u32,",
    "msgdata,open_channel2,commitment_feerate_perkw,u32,",
    "msgdata,open_channel2,funding_satoshis,u64,",
    "msgdata,open_channel2,dust_limit_satoshis,u64,",
    "msgdata,open_channel2,max_htlc_value_in_flight_msat,u64,",
    "msgdata,open_channel2,htlc_minimum_msat,u64,",
    "msgdata,open_channel2,to_self_delay,u16,",
    "msgdata,open_channel2,max_accepted_htlcs,u16,",
    "msgdata,open_channel2,locktime,u32,",
    "msgdata,open_channel2,funding_pubkey,point,",
    "msgdata,open_channel2,revocation_basepoint,point,",
    "msgdata,open_channel2,payment_basepoint,point,",
    "msgdata,open_channel2,delayed_payment_basepoint,point,",
    "msgdata,open_channel2,htlc_basepoint,point,",
    "msgdata,open_channel2,first_per_commitment_point,point,",
    "msgdata,open_channel2,channel_flags,byte,",
    "msgdata,open_channel2,tlvs,opening_tlvs,",
    "tlvtype,opening_tlvs,option_upfront_shutdown_script,1",
    "tlvdata,opening_tlvs,option_upfront_shutdown_script,shutdown_len,u16,",
    "tlvdata,opening_tlvs,option_upfront_shutdown_script,shutdown_scriptpubkey,byte,shutdown_len",
    "msgtype,accept_channel2,65",
    "msgdata,accept_channel2,channel_id,channel_id,",
    "msgdata,accept_channel2,funding_satoshis,u64,",
    "msgdata,accept_channel2,dust_limit_satoshis,u64,",
    "msgdata,accept_channel2,max_htlc_value_in_flight_msat,u64,",
    "msgdata,accept_channel2,htlc_minimum_msat,u64,",
    "msgdata,accept_channel2,minimum_depth,u32,",
    "msgdata,accept_channel2,to_self_delay,u16,",
    "msgdata,accept_channel2,max_accepted_htlcs,u16,",
    "msgdata,accept_channel2,funding_pubkey,point,",
    "msgdata,accept_channel2,revocation_basepoint,point,",
    "msgdata,accept_channel2,payment_basepoint,point,",
    "msgdata,accept_channel2,delayed_payment_basepoint,point,",
    "msgdata,accept_channel2,htlc_basepoint,point,",
    "msgdata,accept_channel2,first_per_commitment_point,point,",
    "msgdata,accept_channel2,tlvs,accept_tlvs,",
    "tlvtype,accept_tlvs,option_upfront_shutdown_script,1",
    "tlvdata,accept_tlvs,option_upfront_shutdown_script,shutdown_len,u16,",
    "tlvdata,accept_tlvs,option_upfront_shutdown_script,shutdown_scriptpubkey,byte,shutdown_len",
    "msgtype,init_rbf,72",
    "msgdata,init_rbf,channel_id,channel_id,",
    "msgdata,init_rbf,funding_satoshis,u64,",
    "msgdata,init_rbf,locktime,u32,",
    "msgdata,init_rbf,funding_feerate_perkw,u32,",
    "msgtype,ack_rbf,73",
    "msgdata,ack_rbf,channel_id,channel_id,",
    "msgdata,ack_rbf,funding_satoshis,u64,",
]

# This is https://github.com/lightningnetwork/lightning-rfc/pull/880
channel_type_csv = [
    "subtype,channel_type",
    "subtypedata,channel_type,len,u16,",
    "subtypedata,channel_type,features,byte,len",
    "tlvtype,open_channel_tlvs,channel_types,1",
    "tlvdata,open_channel_tlvs,channel_types,types,channel_type,...",
    "tlvtype,accept_channel_tlvs,channel_type,1",
    "tlvdata,accept_channel_tlvs,channel_type,type,channel_type,",
]
