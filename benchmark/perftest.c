/*
 * Copyright (c) 2015 Kai Zhang (kay21s@gmail.com)
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 * THE SOFTWARE.
 */


#include "perftest.h"
#include "zipf.h"
#include <argp.h>

// These are all the command line args
long int N_tx = 100000;	// number of transactions
uint16_t key_len = 8; // key length
uint32_t value_len = 64; // value length
int set_percent = 5; // percentage of set operations
int get_percent = 95; // percentage of get operations (100 - set_percent)
uint16_t max_packet_burst = 1;
uint16_t num_max_cores = 4;
uint16_t n_queues = 4;

uint32_t set_len = key_len + value_len;

void *rx_loop(context_t *);
void *tx_loop(context_t *);


benchmark_core_statistics *core_statistics;
struct rte_mempool **recv_pktmbuf_pool; // one for each queue
struct rte_mempool *send_pktmbuf_pool = NULL;
uint64_t *ts_count; 	// one for each queue
uint64_t *ts_total;


/* 1500 bytes MTU + 14 Bytes Ethernet header */
int pktlen;

#if defined(PRELOAD)
int loading_mode = 1;
#endif


/* main processing loop */
void *tx_loop(context_t *context)
{
	struct rte_mbuf *m;
	unsigned i, k;
	struct lcore_queue_conf *qconf;
	unsigned int core_id = context->core_id;
	unsigned int queue_id = context->queue_id;

	unsigned long mask = 1 << core_id;
	// TODO: See other "Disabled CPU affinity" TODOs
//	if (sched_setaffinity(0, sizeof(unsigned long), (cpu_set_t *)&mask) < 0) {
//		printf("core id = %d\n", core_id);
//		assert(0);
//	}

	qconf = &lcore_queue_conf[queue_id];

	unsigned int tmp_pktlen;

	struct ether_hdr *ethh;
	struct ipv4_hdr *iph;
	struct udp_hdr *udph;

	/* for 1GB hash table, 512MB signature, 32bits, total is 128M = 2^29/2^2 = 2^27
	 * load 80% of the hash table */
	const uint32_t total_cnt = (uint32_t)TOTAL_CNT;
	uint32_t preload_cnt = (uint32_t)PRELOAD_CNT;

	struct zipf_gen_state zipf_state;
	mehcached_zipf_init(&zipf_state, (uint64_t)preload_cnt - 2, (double)ZIPF_THETA, (uint64_t)21);
	//printf("LOAD_FACTOR is %f, total key cnt is %d\n", LOAD_FACTOR, total_cnt);

	char *ptr;

	for (i = 0; i < MAX_PKT_BURST; i ++) {
		m = rte_pktmbuf_alloc(send_pktmbuf_pool);
		assert (m != NULL);
		qconf->tx_mbufs[queue_id].m_table[i] = m;

		ethh = (struct ether_hdr *)rte_pktmbuf_mtod(m, unsigned char *);
		//ethh->s_addr = LOCAL_MAC_ADDR;
		ethh->ether_type = rte_cpu_to_be_16((uint16_t)(ETHER_TYPE_IPv4));

		iph = (struct ipv4_hdr *)((unsigned char *)ethh + sizeof(struct ether_hdr));
		iph->version_ihl = 0x40 | 0x05;
		iph->type_of_service = 0;
		iph->packet_id = 0;
		iph->fragment_offset = 0;
		iph->time_to_live = 64;
		iph->next_proto_id = IPPROTO_UDP;
		iph->hdr_checksum = 0;
		iph->src_addr = LOCAL_IP_ADDR;
		iph->dst_addr = KV_IP_ADDR;

		udph = (struct udp_hdr *)((unsigned char *)iph + sizeof(struct ipv4_hdr));
		udph->src_port = LOCAL_UDP_PORT;
		udph->dst_port = KV_UDP_PORT;
		udph->dgram_cksum = 0;

		ptr = (char *)rte_ctrlmbuf_data(m) + EIU_HEADER_LEN;
		*(uint16_t *)ptr = PROTOCOL_MAGIC;
	}

	qconf->tx_mbufs[queue_id].len = MAX_PKT_BURST;


	struct rte_mbuf **m_table;
	uint32_t *ip;
	uint32_t ip_ctr = 1;
	unsigned int port, ret;
	uint32_t get_key = 1, set_key = 1;


#if defined(PRELOAD)

	/* update packet length for 100% SET operations in PRELOAD */
	pktlen = 1510;

	for (i = 0; i < MAX_PKT_BURST; i ++) {
		m = qconf->tx_mbufs[queue_id].m_table[i];
		assert (m != NULL);
		rte_pktmbuf_pkt_len(m) = (uint16_t)pktlen;
		rte_pktmbuf_data_len(m) = (uint16_t)pktlen;

		ethh = (struct ether_hdr *)rte_pktmbuf_mtod(m, unsigned char *);
		iph = (struct ipv4_hdr *)((unsigned char *)ethh + sizeof(struct ether_hdr));
		udph = (struct udp_hdr *)((unsigned char *)iph + sizeof(struct ipv4_hdr));

		iph->total_length = rte_cpu_to_be_16((uint16_t)(pktlen - sizeof(struct ether_hdr)));
		udph->dgram_len = rte_cpu_to_be_16((uint16_t)(pktlen - sizeof(struct ether_hdr) - sizeof(struct ipv4_hdr)));
	}

	uint32_t payload_len;
	if (queue_id == 0) {
		printf("Going to insert %u keys, LOAD_FACTOR is %.2f\n", preload_cnt, LOAD_FACTOR);

		/* preload the keys */
		//while (set_key < NUM_DEFINED_GET * 0.01 * total_cnt) {
		while (set_key < preload_cnt) {
			m_table = (struct rte_mbuf **)qconf->tx_mbufs[queue_id].m_table;

			/* construct a send buffer */
			for (i = 0; i < qconf->tx_mbufs[queue_id].len; i ++) {
				ip = (uint32_t *)((char *)rte_ctrlmbuf_data(m_table[i]) + 26);
				*ip = ip_ctr ++;

				/* skip the packet header and magic number */
				ptr = (char *)rte_ctrlmbuf_data(m_table[i]) + EIU_HEADER_LEN + MEGA_MAGIC_NUM_LEN;
				/* basic length = header len + magic len + ending mark len */
				payload_len = EIU_HEADER_LEN + MEGA_MAGIC_NUM_LEN + MEGA_END_MARK_LEN;

				/* construct a packet */
				/* ----------------------------------------------------- */
				while (payload_len + set_len <= ETHERNET_MAX_FRAME_LEN) {
					*(uint16_t *)ptr = MEGA_JOB_SET;
					ptr += sizeof(uint16_t); /* 2 bytes job type */
					*(uint16_t *)ptr = key_len;
					ptr += sizeof(uint16_t); /* 2 bytes key length */
					*(uint32_t *)ptr = value_len;
					ptr += sizeof(uint32_t); /* 4 bytes value length */

					/* 64 bits key */
					if (BITS_INSERT_BUF == 0)
						*(uint32_t *)(ptr + sizeof(uint32_t)) = set_key;
					else
						*(uint32_t *)(ptr + sizeof(uint32_t)) = (rte_bswap32(set_key & 0xff) << (8 - BITS_INSERT_BUF)) | (set_key);
					*(uint32_t *)(ptr) = set_key;

					ptr += key_len;
					ptr += value_len;

					payload_len += set_len;

					set_key ++;
					if (set_key >= preload_cnt) {
						break;
					}
				}

				assert(payload_len < ETHERNET_MAX_FRAME_LEN);
				/* write the ending mark */
				*(uint16_t *)ptr = 0xFFFF;

				/* reduce insert speed */
				int k = 20000;
				while (k > 0) k--;
			}

			port = 0;
			assert(qconf->tx_mbufs[queue_id].len == MAX_PKT_BURST);
			ret = rte_eth_tx_burst(port, (uint16_t)queue_id, m_table, (uint16_t)qconf->tx_mbufs[queue_id].len);
		}

		printf("\e[32m ==========================     Hash table has been loaded     ========================== \e[0m\n");

		loading_mode = 0;
	}

	while (loading_mode == 1) ;

	/* Different receivers use different keys start point */
	get_key = (10000 * queue_id) % preload_cnt;
	set_key = preload_cnt + queue_id * ((total_cnt - preload_cnt) / n_queues);
#endif

	/* update packet length for the workload packets */
	pktlen = length_packet[WORKLOAD_ID];

	for (i = 0; i < max_packet_burst; i ++) {
		m = qconf->tx_mbufs[queue_id].m_table[i];
		assert (m != NULL);
		rte_pktmbuf_pkt_len(m) = (uint16_t)pktlen;
		rte_pktmbuf_data_len(m) = (uint16_t)pktlen;

		ethh = (struct ether_hdr *)rte_pktmbuf_mtod(m, unsigned char *);
		iph = (struct ipv4_hdr *)((unsigned char *)ethh + sizeof(struct ether_hdr));
		udph = (struct udp_hdr *)((unsigned char *)iph + sizeof(struct ipv4_hdr));

		iph->total_length = rte_cpu_to_be_16((uint16_t)(pktlen - sizeof(struct ether_hdr)));
		udph->dgram_len = rte_cpu_to_be_16((uint16_t)(pktlen - sizeof(struct ether_hdr) - sizeof(struct ipv4_hdr)));
	}

	if (queue_id == 0) {
		gettimeofday(&startime, NULL);
	}
	core_statistics[core_id].enable = 1;
	/* NOW SEARCH AND INSERT */
	// ===========================================================
	while (1) {
		assert (qconf->tx_mbufs[queue_id].len == max_packet_burst);
		m_table = (struct rte_mbuf **)qconf->tx_mbufs[queue_id].m_table;
		for (i = 0; i < qconf->tx_mbufs[queue_id].len; i ++) {
			ip = (uint32_t *)((char *)rte_ctrlmbuf_data(m_table[i]) + 26);
			*ip = ip_ctr ++;

			/* skip the packet header and magic number */
			ptr = (char *)rte_ctrlmbuf_data(m_table[i]) + EIU_HEADER_LEN + MEGA_MAGIC_NUM_LEN;

			for (k = 0; k < number_packet_get[WORKLOAD_ID]; k ++) {
				*(uint16_t *)ptr = MEGA_JOB_GET;
				/* skip job_type, key length = 4 bytes in total */
				ptr += sizeof(uint16_t);
				*(uint16_t *)ptr = key_len;
				ptr += sizeof(uint16_t);

				get_key = (uint32_t)mehcached_zipf_next(&zipf_state) + 1;
				assert(get_key >= 1 && get_key <= preload_cnt);

				/* here we try to evenly distribute the key through insert bufs,
				 * on the first 32 bits, the highest 5 bits are used for 32 insert bufs,
				 * htonl(key & 0xff) << 3 is to assign the 5 bits.
				 * We also need to distribute keys among buckets, and it is the lower
				 * bits are used for hash. the "|key" is setting the hash.
				 * The next 32 bits are used as signature, just key ++ */
				if (BITS_INSERT_BUF == 0)
					*(uint32_t *)(ptr + sizeof(uint32_t)) = get_key;
				else
					*(uint32_t *)(ptr + sizeof(uint32_t)) = (rte_bswap32(get_key & 0xff) << (8 - BITS_INSERT_BUF)) | get_key;
				*(uint32_t *)(ptr) = get_key;

				ptr += key_len;
			}

			for (k = 0; k < number_packet_set[WORKLOAD_ID]; k ++) {
				*(uint16_t *)ptr = MEGA_JOB_SET;
				ptr += sizeof(uint16_t);
				*(uint16_t *)ptr = key_len;
				ptr += sizeof(uint16_t);
				*(uint32_t *)ptr = value_len;
				ptr += sizeof(uint32_t);

				set_key ++;
#if defined(PRELOAD)
				if (set_key >= preload_cnt + (queue_id + 1) * ((total_cnt - preload_cnt) / n_queues)) {
					// FIXME
					assert(0);
				}
#else
				if (set_key >= total_cnt) {
					set_key = 1;
				}
#endif

				if (BITS_INSERT_BUF == 0)
					*(uint32_t *)(ptr + sizeof(uint32_t)) = set_key;
				else
					*(uint32_t *)(ptr + sizeof(uint32_t)) = (rte_bswap32(set_key & 0xff) << (8 - BITS_INSERT_BUF)) | (set_key);
				*(uint32_t *)(ptr) = set_key;

				ptr += key_len;
				ptr += value_len;
			}
			//total_cnt += number_packet_set[WORKLOAD_ID];

			*(uint16_t *)ptr = 0xFFFF;
		}

		for (i = 0; i < qconf->tx_mbufs[queue_id].len; i ++) {
			/* use an IP field for measuring latency, disabled  */
			//*(uint64_t *)((char *)rte_ctrlmbuf_data(m_table[i]) + ETHERNET_HEADER_LEN + 4) = rte_rdtsc_precise();
			if (rte_pktmbuf_pkt_len(m) != length_packet[WORKLOAD_ID]) {
				printf("%d != %d\n", rte_pktmbuf_pkt_len(m), length_packet[WORKLOAD_ID]);
				assert(0);
			}
		}

		port = 0;
		assert(qconf->tx_mbufs[queue_id].len == max_packet_burst);
		ret = rte_eth_tx_burst(port, (uint16_t) queue_id, m_table, (uint16_t) qconf->tx_mbufs[queue_id].len);
		core_statistics[core_id].tx += ret;
		if (unlikely(ret < qconf->tx_mbufs[queue_id].len)) {
			core_statistics[core_id].dropped += (qconf->tx_mbufs[queue_id].len - ret);
		}
	}
}

/* main processing loop */
void *rx_loop(context_t *context)
{
	struct rte_mbuf *pkts_burst[max_packet_burst];
	struct rte_mbuf *m;
	unsigned int core_id = context->core_id;
	unsigned int queue_id = context->queue_id;
	uint64_t prev_tsc, diff_tsc, cur_tsc, timer_tsc;
	unsigned portid, nb_rx;

	unsigned long mask = 1 << core_id;
	// TODO: See other "Disabled CPU affinity" TODOs
//	if (sched_setaffinity(0, sizeof(unsigned long), (cpu_set_t *)&mask) < 0) {
//		assert(0);
//	}

	prev_tsc = 0;
	timer_tsc = 0;

	core_statistics[core_id].enable = 1;

	while (1) {

		cur_tsc = rte_rdtsc();
		diff_tsc = cur_tsc - prev_tsc;

		/* if timer is enabled */
		if (timer_period > 0) {
			/* advance the timer */
			timer_tsc += diff_tsc;
			/* if timer has reached its timeout */
			if (unlikely(timer_tsc >= (uint64_t) timer_period)) {
				/* do this only on master core */
#if defined(PRELOAD)
				if (queue_id == 0 && loading_mode == 0) {
#else
				if (queue_id == 0) {
#endif
					print_stats();
					/* reset the timer */
					timer_tsc = 0;
				}
			}
		}
		prev_tsc = cur_tsc;

		/*
		 * Read packet from RX queues
		 */

		portid = 0;
		nb_rx = rte_eth_rx_burst((uint8_t) portid, queue_id, pkts_burst, max_packet_burst);

		core_statistics[core_id].rx += nb_rx;

		if (nb_rx > 0) {
			m = pkts_burst[0];
			rte_prefetch0(rte_pktmbuf_mtod(m, void *));

			//uint64_t now = rte_rdtsc_precise();
			uint64_t now = rte_rdtsc();
			uint64_t ts = *(uint64_t *)((char *)rte_ctrlmbuf_data(m) + ETHERNET_HEADER_LEN + 4);
			if (ts != 0) {
				ts_total[queue_id] += now - ts;
				ts_count[queue_id] ++;
			}
		}

		if (nb_rx > 0) {
			unsigned k = 0;
			do {
				rte_pktmbuf_free(pkts_burst[k]);
			} while (++k < nb_rx);
		}
	}
}


void parse_args(int argc, char **argv);
void print_args();


int
MAIN(int argc, char **argv)
{
	int ret;
	int i;
	uint8_t nb_ports;
	uint8_t portid, queue_id;

	parse_args(argc, argv);
	print_args();

	set_len = key_len + value_len;
	core_statistics = (struct benchmark_core_statistics*)
	                  malloc(num_max_cores * sizeof(struct benchmark_core_statistics));
	ts_count = (uint64_t*) malloc(n_queues * sizeof(uint64_t));
	ts_total = (uint64_t*) malloc(n_queues * sizeof(uint64_t));
	recv_pktmbuf_pool = (struct rte_mempool**) malloc(n_queues * sizeof(struct rte_mempool*));
	lcore_queue_conf = (lcore_queue_conf *) malloc(n_queues * sizeof(struct lcore_queue_conf));
	// Initialise properly the lcore_queue_conf
	// we have num_queue of those
	// each has MAX_TX_QUEUE_PER_PORT tx_mbufs
	// each with an *m_table, that needs to have size max_packet_burst
	for (int i = 0; i < n_queues; ++i)
		for (int j = 0; j < MAX_TX_QUEUE_PER_PORT; ++j)
			lcore_queue_conf[i].tx_mbufs[j].m_table = (struct rte_mbuf *)
			        malloc(max_packet_burst * sizeof (struct rte_mbuf*));

	/* init EAL */
	int t_argc = 5;
	char *t_argv[] = {"./build/benchmark", "-c", "f", "-n", "1"};
	ret = rte_eal_init(t_argc, t_argv);
	if (ret < 0)
		rte_exit(EXIT_FAILURE, "Invalid EAL arguments\n");

	char str[10];
	/* create the mbuf pool */
	for (i = 0; i < n_queues; i ++) {
		sprintf(str, "%d", i);
		recv_pktmbuf_pool[i] =
		    rte_mempool_create(str, NB_MBUF,
		                       MBUF_SIZE, 32,
		                       sizeof(struct rte_pktmbuf_pool_private),
		                       rte_pktmbuf_pool_init, NULL,
		                       rte_pktmbuf_init, NULL,
		                       rte_socket_id(), 0);
		if (recv_pktmbuf_pool[i] == NULL)
			rte_exit(EXIT_FAILURE, "Cannot init mbuf pool\n");
	}

	send_pktmbuf_pool =
	    rte_mempool_create("send_mbuf_pool", NB_MBUF,
	                       MBUF_SIZE, 32,
	                       sizeof(struct rte_pktmbuf_pool_private),
	                       rte_pktmbuf_pool_init, NULL,
	                       rte_pktmbuf_init, NULL,
	                       rte_socket_id(), 0);
	if (send_pktmbuf_pool == NULL)
		rte_exit(EXIT_FAILURE, "Cannot init mbuf pool\n");

	if (rte_eal_pci_probe() < 0)
		rte_exit(EXIT_FAILURE, "Cannot probe PCI\n");

	nb_ports = rte_eth_dev_count();
	assert (nb_ports == 1);

	/* Initialise each port */
	for (portid = 0; portid < nb_ports; portid++) {
		/* init port */
		printf("Initializing port %u... ", (unsigned) portid);
		ret = rte_eth_dev_configure(portid, n_queues, n_queues, &port_conf);
		if (ret < 0)
			rte_exit(EXIT_FAILURE, "Cannot configure device: err=%d, port=%u\n",
			         ret, (unsigned) portid);

		for (queue_id = 0; queue_id < n_queues; queue_id ++) {
			/* init RX queues */
			ret = rte_eth_rx_queue_setup(portid, queue_id, nb_rxd,
			                             rte_eth_dev_socket_id(portid), &rx_conf,
			                             recv_pktmbuf_pool[queue_id]);
			if (ret < 0)
				rte_exit(EXIT_FAILURE, "rte_eth_rx_queue_setup:err=%d, port=%u\n",
				         ret, (unsigned) portid);

			/* init TX queues */
			ret = rte_eth_tx_queue_setup(portid, queue_id, nb_txd,
			                             rte_eth_dev_socket_id(portid), &tx_conf);
			if (ret < 0)
				rte_exit(EXIT_FAILURE, "rte_eth_tx_queue_setup:err=%d, port=%u\n",
				         ret, (unsigned) portid);
		}

		/* Start device */
		ret = rte_eth_dev_start(portid);
		if (ret < 0)
			rte_exit(EXIT_FAILURE, "rte_eth_dev_start:err=%d, port=%u\n",
			         ret, (unsigned) portid);

		printf("done: \n");

		rte_eth_promiscuous_enable(portid);

		/* initialize port stats */
		memset(&core_statistics, 0, sizeof(core_statistics));
	}
	fflush(stdout);

	check_all_ports_link_status(nb_ports, 0);

	for (i = 0; i < n_queues; i ++) {
		ts_total[i] = 0;
		ts_count[i] = 1;
	}

	pthread_t tid;
	pthread_attr_t attr;

	pthread_attr_init(&attr);
	pthread_attr_setdetachstate(&attr, PTHREAD_CREATE_DETACHED);

	context_t *context;

	for (i = 0; i < n_queues; i ++) {
		if (i == 0) {
			context = (context_t *) malloc (sizeof(context_t));
			context->core_id = 0;
			context->queue_id = i;
			if (pthread_create(&tid, &attr, (void *)rx_loop, (void *)context) != 0) {
				perror("pthread_create error!!\n");
			}
		}

		context = (context_t *) malloc (sizeof(context_t));
#if defined(AFFINITY_MAX_QUEUE)
		context->core_id = i + 1;
#elif defined(AFFINITY_ONE_NODE)
		context->core_id = i * 2 + 1;
#else
		printf("No affinity\n");
		exit(0);
#endif
		context->queue_id = i;
		if (pthread_create(&tid, &attr, (void *)tx_loop, (void *)context) != 0) {
			perror("pthread_create error!!\n");
		}
	}

	while (1) {
		sleep(10);
	}
	// optionally, free allocated structures

	return 0;
}

const char *argp_program_version = "perftest 1.0";
const char *argp_program_bug_address = "<your@email.address>";
static char doc[] = "Benchmarking MegaKV transactions.";
static char args_doc[] = "[FILENAME]...";
static struct argp_option options[] = {
	{ "help", 'h', 0, 0, "Print useage and exit."},
	{ "transactions", 'n', 0, 0, "Number of transactions (default: 100K)."},
	{ "keylen", 'k', 0, 0, "Key length (default: 8 bytes)"},
	{ "valuelen", 'v', 0, 0, "Value length (default: 64 bytes)."},
	{ "set", 's', 0, 0, "Set percent (default: 5%)."},
	{ "get", 'g', 0, 0, "Get percent (default: 95%)."},
	{ "cores", 'c', 0, 0, "Max number of cores (default: 4)"},
	{ "burst", 'b', 0, 0, "Max packet burst (default: 1)"},
	{ "queues", 'q', 0, 0, "Num Queues (default: 4)."},
	{ 0 }
};

struct arguments {
	long int n;
	uint16_t k;
	uint32_t v;
	uint16_t s;
	uint16_t g;
	uint16_t c;
	uint16_t b;
	uint16_t q;
};


static error_t parse_opt(int key, char *arg, struct argp_state *state) {
	struct arguments *arguments = state->input;
	switch (key) {
	case 'h':
		argp_usage(state);
		break;
	case 'n':
		N_tx = atoi(arg);
		assert(N_tx > 0);
		break;
	case 'k':
		key_len = atoi(arg);
		assert(key_len > 0);
		break;
	case 'v':
		value_len = atoi(arg);
		assert(value_len > 0);
		break;
	case 's':
		set_percent = atoi(arg);
		assert(set_percent <= 100 && set_percent >= 0);
		get_percent = 100 - set_percent;
		break;
	case 'g':
		get_percent = atoi(arg);
		assert(get_percent <= 100 && get_percent >= 0);
		set_percent = 100 - get_percent;
		break;
	case 'c':
		num_max_cores = atoi(arg);
		assert(num_max_cores > 0);
		break;
	case 'b':
		max_packet_burst = atoi(arg);
		assert(max_packet_burst > 0);
		break;
	case 'q':
		n_queues = atoi(arg);
		assert(n_queues > 0);
		break;
	case ARGP_KEY_ARG: break;
	case ARGP_KEY_END: break;
	default: return ARGP_ERR_UNKNOWN;
	}
	return 0;
}

static struct argp argp = { options, parse_opt, args_doc, doc };

void parse_args(int argc, char **argv)
{
	argp_parse(&argp, argc, argv, 0, 0, &arguments);
}


void print_args()
{
	printf("Number of transactions: %d\n", N_tx);
	printf("Key length: %d\n", key_len);
	printf("Value length: %d\n", val_len);
	printf("Set percent: %d\n", set_percent);
	printf("Get percent: %d\n", get_percent);
	printf("Max cores: %d\n", num_max_cores);
	printf("Max packet burst: %d\n", max_packet_burst);
	printf("Num queues: %d\n", n_queues);
}



// enum optionIndex {
//     UNKNOWN,
//     HELP,
//     N_TX,
//     KEY_LEN,
//     VALUE_LEN,
//     SET_PERCENT,
//     GET_PERCENT,
//     N_MAX_CORES,
//     N_MAX_PKT_BURST,
//     N_QUEUES,
//     OPTIONS_NUM
// };

// const option::Descriptor usage[] = {
//     {
//         UNKNOWN, 0, "", "", Arg::None, "USAGE: ./perftest [options]\n\n"
//         "Options:"
//     },
//     {
//         HELP, 0, "h", "help", Arg::None,
//         "  --help,              -h        Print usage and exit."
//     },
//     {
//         N_TX, 0, "n", "transactions", util::Arg::Numeric,
//         "  --transactions=<num>,       -n <num>  Number of transactions (default: 100K)"
//     },
//     {
//         KEY_LEN, 0, "k", "keylen", util::Arg::Numeric,
//         "  --keylen=<num>,       -k <num>  Key length (default: 8 bytes)"
//     },
//     {
//         VALUE_LEN, 0, "v", "valuelen", util::Arg::Numeric,
//         "  --valuelen=<num>,       -v <num>  Value length (default: 64 bytes)"
//     },
//     {
//         SET_PERCENT, 0, "s", "set", util::Arg::Numeric,
//         "  --set=<num>,       -s <num>  Set percent (default: 5%)"
//     },
//     {
//         GET_PERCENT, 0, "g", "get", util::Arg::Numeric,
//         "  --get=<num>,       -g <num>  Get percent (default: 95%)"
//     },
//     {
//         N_MAX_CORES, 0, "c", "cores", util::Arg::Numeric,
//         "  --cores=<num>,       -c <num> Max number of cores (default: 4)"
//     },
//     {
//         N_MAX_PKT_BURST, 0, "b", "burst", util::Arg::Numeric,
//         "  --burst=<num>,       -b <num> Max packet burst (default: 1)"
//     },
//     {
//         N_QUEUES, 0, "q", "queues", util::Arg::Numeric,
//         "  --queues=<num>,       -q <num> Num Queues (default: 4)"
//     },
//     {
//         UNKNOWN, 0, "", "", Arg::None,
//         "\nExamples:\n"
//         "\t./perftest\n"
//         "\t./perftest -k 16 -v 64 -n10000\n"
//     },
//     {0, 0, 0, 0, 0, 0}
// };

// argc -= (argc > 0);
// argv += (argc > 0); // skip program name argv[0] if present
// Stats stats(usage, argc, argv);
// vector<Option> options(stats.options_max);
// vector<Option> buffer(stats.buffer_max);
// Parser parse(usage, argc, argv, &options[0], &buffer[0]);

// if (options[HELP]) {
//     printUsage(cout, usage);
//     exit(0);
// }

// for (int i = 0; i < parse.optionsCount(); ++i) {
//     Option &opt = buffer[i];
//     // fprintf(stdout, "Argument #%d is ", i);
//     switch (opt.index()) {
//     case HELP:
//     // not possible, because handled further above and exits the program
//     case N_TX:
//         N_tx = atoi(opt.arg);
//         assert(N_tx > 0);
//         // fprintf(stdout, "--numeric with argument '%s'\n", opt.arg);
//         break;
//     case KEY_LEN:
//         key_len = atoi(opt.arg);
//         assert(key_len > 0);
//         // fprintf(stdout, "--numeric with argument '%s'\n", opt.arg);
//         break;
//     case VALUE_LEN:
//         value_len = atoi(opt.arg);
//         assert(value_len > 0);
//         // fprintf(stdout, "--numeric with argument '%s'\n", opt.arg);
//         break;
//     case SET_PERCENT:
//         set_percent = atoi(opt.arg);
//         assert(set_percent <=100 && set_percent>=0);
//         get_percent = 100 - set_percent;
//         // fprintf(stdout, "--numeric with argument '%s'\n", opt.arg);
//         break;
//     case GET_PERCENT:
//         get_percent = atoi(opt.arg);
//         assert(get_percent <=100 && get_percent>=0);
//         set_percent = 100 - get_percent;
//         // fprintf(stdout, "--numeric with argument '%s'\n", opt.arg);
//         break;
//     case N_MAX_CORES:
//         num_max_cores = atoi(opt.arg);
//         assert(num_max_cores > 0);
//         // fprintf(stdout, "--numeric with argument '%s'\n", opt.arg);
//         break;
//     case N_MAX_PKT_BURST:
//         max_packet_burst = atoi(opt.arg);
//         assert(max_packet_burst > 0);
//         // fprintf(stdout, "--numeric with argument '%s'\n", opt.arg);
//         break;
//     case N_QUEUES:
//         n_queues = atoi(opt.arg);
//         assert(n_queues > 0);
//         // fprintf(stdout, "--numeric with argument '%s'\n", opt.arg);
//         break;

//     case UNKNOWN:
//         // not possible because Arg::Unknown returns ARG_ILLEGAL
//         // which aborts the parse with an error
//         break;
//     }
// }