package tn.esprit.awd.candidate.service;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import tn.esprit.awd.candidate.dto.AddressRequest;
import tn.esprit.awd.candidate.dto.AddressResponse;
import tn.esprit.awd.candidate.entity.Address;
import tn.esprit.awd.candidate.exception.ResourceNotFoundException;
import tn.esprit.awd.candidate.mapper.CandidateMapper;
import tn.esprit.awd.candidate.repository.AddressRepository;

import java.util.List;

@Service
@Transactional
public class AddressService {

    private final AddressRepository addressRepository;

    public AddressService(AddressRepository addressRepository) {
        this.addressRepository = addressRepository;
    }

    @Transactional(readOnly = true)
    public List<AddressResponse> findAll() {
        return addressRepository.findAll().stream().map(CandidateMapper::toResponse).toList();
    }

    @Transactional(readOnly = true)
    public AddressResponse findById(Long id) {
        return CandidateMapper.toResponse(getAddress(id));
    }

    public AddressResponse create(AddressRequest request) {
        return CandidateMapper.toResponse(addressRepository.save(CandidateMapper.toEntity(request)));
    }

    public AddressResponse update(Long id, AddressRequest request) {
        Address address = getAddress(id);
        CandidateMapper.updateEntity(address, request);
        return CandidateMapper.toResponse(address);
    }

    public void delete(Long id) {
        Address address = getAddress(id);
        if (address.getCandidate() != null) {
            address.getCandidate().setAddress(null);
        }
        addressRepository.delete(address);
    }

    Address getAddress(Long id) {
        return addressRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Address", id));
    }
}
